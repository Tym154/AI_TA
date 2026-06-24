from pathlib import Path
from langchain_core.tools import tool

@tool
def read_pipeline_docs() -> str:
    """Reads the studio's strict naming conventions. 
    ALWAYS call this tool before executing any Blender script to ensure you save the file correctly.
    """
    doc_path = Path("./mock_studio_library/naming_conventions.txt").resolve()
    
    try:
        if doc_path.exists():
            # Force utf-8 to prevent weird encoding crashes
            return doc_path.read_text(encoding="utf-8")
        else:
            # Provide a default rule so the AI doesn't get stuck
            return (
                "WARNING: pipeline_docs.txt is missing from the server. "
                "Use the emergency fallback convention: EMERGENCY_[YYYYMMDD]_[SceneName]_v001.blend"
            )
    except Exception as e:
        return f"Tool Error: Failed to read docs. {str(e)}"