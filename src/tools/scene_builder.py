import subprocess
import tempfile
import ast
from pathlib import Path
from langchain_core.tools import tool

def _is_safe_code(code: str) -> tuple[bool, str]:
    """Scans the AI's python code for malicious or forbidden imports."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax Error in generated code on line {e.lineno}: {e.msg}"
        
    forbidden_modules = {'os', 'sys', 'subprocess', 'shutil', 'socket', 'requests'}
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            # Check for generic imports and from ... import ...
            module_names = [alias.name.split('.')[0] for alias in getattr(node, 'names', [])]
            if getattr(node, 'module', None):
                module_names.append(node.module.split('.')[0])
                
            for mod in module_names:
                if mod in forbidden_modules:
                    return False, f"Security Violation: Importing '{mod}' is strictly forbidden in pipeline scripts."
    
    return True, "Safe"


@tool
def execute_blender_script(python_code: str, output_filename: str) -> str:
    """Executes generated Python code inside Blender.
    Input the raw python code and the desired output filename (e.g. CYB_sq01_sh010_LAY_v001.blend).
    """
    # Security Scan
    is_safe, scan_msg = _is_safe_code(python_code)
    if not is_safe:
        return f"Tool Execution Blocked. {scan_msg}. Please rewrite the code without this module."

    output_path = Path.cwd() / "mock_studio_library/scenes" / output_filename

    # Write temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_script:
        save_command = f"\n\nimport bpy\nbpy.ops.wm.save_as_mainfile(filepath=r'{output_path}')"
        temp_script.write(python_code + save_command)
        script_path = Path(temp_script.name)

    # Execute with strict timeouts and combined output capture
    try:
        subprocess.run(
            ["blender", "-b", "-P", str(script_path), "--python-exit-code", "1"],
            capture_output=True,
            text=True,
            check=True,
            timeout=45
        )
        script_path.unlink(missing_ok=True)
        
        # Validation
        if output_path.exists():
            if output_path.stat().st_size > 0:
                return f"Success! Scene generated and verified. Saved to: {output_path.name}"
            else:
                output_path.unlink() # Delete the corrupt zero-byte file
                return "Failed: Blender executed, but the resulting .blend file was 0 bytes (corrupt)."
        else:
            return "Failed: Blender exited without throwing an error, but no file was saved. Check your file path logic."
            
    except subprocess.TimeoutExpired:
        script_path.unlink(missing_ok=True)
        return "Execution Failed: Script timed out after 45 seconds. You likely wrote an infinite loop."
        
    except subprocess.CalledProcessError as e:
        script_path.unlink(missing_ok=True)
        error_context = f"STDERR:\n{e.stderr}\n\nSTDOUT (Last 500 chars):\n{e.stdout[-500:]}"
        return f"Blender Execution Failed. Error Log:\n{error_context}"