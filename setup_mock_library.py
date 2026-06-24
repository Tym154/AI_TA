import os

"""Sets up a mock folder system that the tools can use to store and fetch mock assets
(In the initialization prompt it says to generate the assets from scratch even if it finds the needed asset.
Because i do not have any assest to use)"""
def create_mock_library():
    """Creates dummy folders and files for the agent to find."""
    folders = [
        "mock_studio_library/characters",
        "mock_studio_library/environments"
        "mock_studio_library/scenes"
    ]
    
    files = [
        "mock_studio_library/characters/cyborg.fbx",
        "mock_studio_library/characters/alien_mutant.obj",
        "mock_studio_library/environments/sci_fi_hallway.blend",
        "mock_studio_library/environments/abandoned_warehouse.blend"
    ]

    # Create directories
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        print(f"Created directory: {folder}")

    # Create empty dummy files
    for file in files:
        with open(file, 'w') as f:
            f.write("DUMMY ASSET DATA")
        print(f"Created dummy asset: {file}")

if __name__ == "__main__":
    create_mock_library()