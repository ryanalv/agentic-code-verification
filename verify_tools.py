import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.utils.file_tools import list_project_structure, read_specific_file

def test_tools():
    print("=== Testing list_project_structure ===")
    structure = list_project_structure(os.getcwd())
    print(f"Structure Preview:\n{structure[:500]}...")
    
    if "src/" in structure and "server.py" in structure:
        print("\nPASS: Project structure seems correct.")
    else:
        print("\nFAIL: Project structure missing expected files.")

    print("\n=== Testing read_specific_file (Success Case) ===")
    file_path = os.path.join(os.getcwd(), "src", "server.py")
    content = read_specific_file(file_path)
    if "FastAPI" in content:
        print("PASS: Successfully read src/server.py")
    else:
        print(f"FAIL: Failed to read src/server.py. Content preview: {content[:100]}")

    print("\n=== Testing read_specific_file (Error Case) ===")
    ghost_path = os.path.join(os.getcwd(), "src", "ghost_file_xyz.py")
    error_content = read_specific_file(ghost_path)
    if "Error" in error_content and "does not exist" in error_content:
        print("PASS: Correctly handled non-existent file.")
    else:
        print(f"FAIL: Should have returned error for non-existent file. Got: {error_content}")

if __name__ == "__main__":
    test_tools()
