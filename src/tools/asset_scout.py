import os
from pathlib import Path
from langchain_core.tools import tool

@tool
def search_studio_library(asset_keywords: list[str]) -> str:
    """Searches the local mock_studio_library directory for 3D assets matching the keywords.
    Use this tool BEFORE writing any Blender script to ensure the assets exist.
    """
    if not asset_keywords or not isinstance(asset_keywords, list):
        return "Tool Error: 'asset_keywords' must be a non-empty list of strings."

    base_dir = Path("./mock_studio_library").resolve()
    
    if not base_dir.exists():
        return f"System Error: Library path {base_dir} does not exist. Alert the user."

    found_assets = []
    # Clean keywords to lowercase for robust matching
    clean_keywords = [str(k).lower() for k in asset_keywords]

    for root, _, files in os.walk(base_dir):
        # Ensuring we are still inside the base directory
        if not Path(root).resolve().is_relative_to(base_dir):
            continue
            
        for file in files:
            # Match if ANY keyword is in the filename
            if any(keyword in file.lower() for keyword in clean_keywords):
                full_path = Path(root) / file
                found_assets.append(str(full_path))
                
                # Stop at 10 results to protect LLM token limits
                if len(found_assets) >= 10:
                    break
        if len(found_assets) >= 10:
            break

    if not found_assets:
        return f"Search Result: No assets found matching keywords: {clean_keywords}."
        
    return f"Search Result (Found {len(found_assets)}): \n" + "\n".join(found_assets)