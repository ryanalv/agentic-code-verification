import os
import sys

# Ensure src in path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.code_analyst import analyze_codebase

def test_run():
    project_path = os.path.join(PROJECT_ROOT, "src")
    print(f"Testing project path: {project_path}")
    result = analyze_codebase(project_path, "SourceCode")
    print("FINISHED ANALYSIS")
    print("Steps:", result.get("steps"))
    details = result.get("details", {})
    draft = details.get("draft_response", "")
    print(f"Draft Response Length: {len(draft)} caracteres.")
    if len(draft) > 500:
        print("Preview:", draft[:500])

if __name__ == "__main__":
    test_run()
