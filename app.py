import os
from pathlib import Path
from dotenv import load_dotenv

current_dir = Path(__file__).parent
env_path = current_dir / ".env"
load_dotenv(dotenv_path=env_path)

import streamlit as st
import uuid
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from src.graph import app as agent_app

# UI configuration
st.set_page_config(page_title="AI Pipeline TD", layout="wide", initial_sidebar_state="expanded")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "pending_action" not in st.session_state:
    st.session_state.pending_action = None
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None
if "feedback_text" not in st.session_state:
    st.session_state.feedback_text = None
if "show_pending_details" not in st.session_state:
    st.session_state.show_pending_details = False
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False

config = {"configurable": {"thread_id": st.session_state.thread_id}}

# SIdebar
with st.sidebar:
    st.title("Scene Copilot")
    st.divider()
    
    if st.button("New Conversation", use_container_width=True, type="primary", disabled=st.session_state.is_processing):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.pending_action = None
        st.session_state.show_pending_details = False
        st.rerun()
        
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Studio Settings")
    selected_persona = st.selectbox(
        "Agent Persona", 
        ["Professional", "Grumpy Senior TD", "Junior Pipeline Engineer"],
        disabled=st.session_state.is_processing
    )
    st.caption(f"Session ID: {st.session_state.thread_id[:8]}")

# Current state fetch
state = agent_app.get_state(config)
is_paused = state.next and state.next[0] == "tools"

# Render history
if state.values and "messages" in state.values:
    messages = state.values["messages"]
    
    for i, msg in enumerate(messages):
        # User Messages
        if isinstance(msg, HumanMessage):
            if not msg.content.startswith("[Correction requested]"):
                with st.chat_message("user"):
                    st.markdown(msg.content)
                
        # AI Messages & Tools
        elif isinstance(msg, AIMessage):
            with st.chat_message("assistant"):
                readable_text = ""
                if isinstance(msg.content, str):
                    readable_text = msg.content
                elif isinstance(msg.content, list):
                    text_blocks = [b["text"] for b in msg.content if isinstance(b, dict) and b.get("type") == "text"]
                    readable_text = "\n".join(text_blocks)
                    
                if readable_text.strip():
                    st.markdown(readable_text)
                    
                # Persistent Historical Logs
                if getattr(msg, "tool_calls", None):
                    is_current_pending = is_paused and i == len(messages) - 1
                    
                    if not is_current_pending:
                        log_key = f"show_log_{i}"
                        if log_key not in st.session_state:
                            st.session_state[log_key] = False
                            
                        if not st.session_state[log_key]:
                            if st.button("View Logs", key=f"btn_open_{i}", disabled=st.session_state.is_processing):
                                st.session_state[log_key] = True
                                st.rerun()
                        else:
                            with st.container(border=True):
                                st.markdown("##### Execution:")
                                for tool_call in msg.tool_calls:
                                    st.markdown(f"- **Target Node:** `{tool_call['name']}`")
                                    args = tool_call['args']
                                    if args:
                                        with st.expander("Show Payload Data", expanded=False):
                                            if 'python_code' in args:
                                                st.code(args['python_code'], language="python")
                                            else:
                                                st.json(args)
                                
                                st.divider()
                                
                                st.markdown("##### Execution Results:")
                                j = i + 1
                                while j < len(messages) and isinstance(messages[j], ToolMessage):
                                    t_msg = messages[j]
                                    if "Failed" in t_msg.content or "Error" in t_msg.content:
                                        st.markdown(f"**Failed:** `{t_msg.name}`")
                                    else:
                                        st.markdown(f"**Success:** `{t_msg.name}`")
                                    j += 1
                                    
                                st.markdown("<br>", unsafe_allow_html=True)
                                if st.button("\u2227" + " Collapse Logs", key=f"btn_close_{i}", disabled=st.session_state.is_processing):
                                    st.session_state[log_key] = False
                                    st.rerun()

# Execution of a task
if st.session_state.is_processing and st.session_state.pending_action:
    action = st.session_state.pending_action
    st.session_state.pending_action = None  
    
    if action == "prompt":
        prompt = st.session_state.pending_prompt
        with st.chat_message("user"):
            st.markdown(prompt)
        input_data = {"messages": [HumanMessage(content=prompt)], "persona": selected_persona}
    elif action == "approve":
        input_data = None
    elif action == "reject":
        feedback = st.session_state.feedback_text
        current_state = agent_app.get_state(config)
        pending_msg = current_state.values["messages"][-1]
        rejection_messages = [
            ToolMessage(content=f"USER REJECTED THIS ACTION. Feedback: {feedback}", tool_call_id=tc['id']) 
            for tc in pending_msg.tool_calls
        ]
        feedback_log = HumanMessage(content=f"[Correction requested]: {feedback}")
        agent_app.update_state(config, {"messages": rejection_messages + [feedback_log]}, as_node="tools")
        input_data = None

    with st.chat_message("assistant"):
        text_placeholder = st.empty()
        with st.status("Agent processing pipeline tasks...", expanded=True) as status:
            
            current_state = agent_app.get_state(config)
            if current_state.values and "messages" in current_state.values:
                seen_ids = {msg.id for msg in current_state.values["messages"]}
            else:
                seen_ids = set()
                
            has_drawn_divider = False
                
            try:
                for output in agent_app.stream(input_data, config, stream_mode="values"):
                    
                    for msg in output["messages"]:
                        if msg.id not in seen_ids:
                            seen_ids.add(msg.id)
                            
                            # Render Intent
                            if getattr(msg, "tool_calls", None):
                                st.markdown("##### Action Plan:")
                                for tool in msg.tool_calls:
                                    st.markdown(f"- Preparing to execute: `{tool['name']}`")
                                    
                            # Render execution results
                            elif isinstance(msg, ToolMessage):
                                if not has_drawn_divider:
                                    st.divider()
                                    st.markdown("##### Execution Logs")
                                    has_drawn_divider = True
                                    
                                if "Failed" in msg.content or "Error" in msg.content:
                                    st.markdown(f"**Failed:** `{msg.name}`")
                                else:
                                    st.markdown(f"**Success:** `{msg.name}`")
                                    
                            elif isinstance(msg, AIMessage):
                                readable_text = ""
                                if isinstance(msg.content, str):
                                    readable_text = msg.content
                                elif isinstance(msg.content, list):
                                    text_blocks = [b["text"] for b in msg.content if isinstance(b, dict) and b.get("type") == "text"]
                                    readable_text = "\n".join(text_blocks)
                                    
                                if readable_text.strip():
                                    text_placeholder.markdown(readable_text)
                
                status.update(label="Execution Complete", state="complete", expanded=False)
            finally:
                st.session_state.is_processing = False
                
    st.rerun()

# Execution approval
ui_container = st.empty()
with ui_container.container():
    if not st.session_state.is_processing:
        if is_paused:
            pending_message = state.values["messages"][-1]
            st.divider()
            st.info("Pipeline Safety Check: Agent requests permission to execute tools.")
            
            if not st.session_state.show_pending_details:
                if st.button("View Details & Generated Code", use_container_width=True):
                    st.session_state.show_pending_details = True
                    st.rerun()
            else:
                with st.container(border=True):
                    st.markdown("##### Pending Plan")
                    for tool_call in pending_message.tool_calls:
                        st.markdown(f"- **Target Node:** `{tool_call['name']}`")
                        args = tool_call['args']
                        
                        if args:
                            if 'python_code' in args:
                                st.code(args['python_code'], language="python")
                                if 'output_filename' in args:
                                    st.markdown(f"**Output Filename:** `{args['output_filename']}`")
                            else:
                                st.json(args)
                        else:
                            st.markdown("*No input arguments required for this tool.*")
                        st.markdown("---")
                        
                    if st.button("\u2227" + " Collapse Code View", use_container_width=True):
                        st.session_state.show_pending_details = False
                        st.rerun()
                        
            st.markdown("<br>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("APPROVE & EXECUTE", use_container_width=True, type="primary"):
                    ui_container.empty() 
                    st.session_state.show_pending_details = False
                    st.session_state.pending_action = "approve"
                    st.session_state.is_processing = True 
                    st.rerun()
                    
            with col2:
                with st.popover("REJECT & EDIT", use_container_width=True):
                    st.markdown("**Request Code Changes**")
                    feedback = st.text_area("Provide feedback to the agent:")
                    if st.button("Submit Feedback", type="primary"):
                        ui_container.empty() 
                        st.session_state.show_pending_details = False
                        st.session_state.feedback_text = feedback
                        st.session_state.pending_action = "reject"
                        st.session_state.is_processing = True 
                        st.rerun()
        else:
            user_prompt = st.chat_input("Enter scene description or pipeline request...", disabled=st.session_state.is_processing)
            if user_prompt:
                ui_container.empty() 
                st.session_state.pending_action = "prompt"
                st.session_state.pending_prompt = user_prompt
                st.session_state.is_processing = True 
                st.rerun()