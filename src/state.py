from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # add_messages appends new messages rather than overwriting the whole list
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # State variables specific to a pipeline
    user_prompt: str
    persona: str
    found_assets: list[str]
    generated_blender_code: str
    scene_file_path: str