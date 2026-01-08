# Utilitário para leitura recursiva de arquivos do projeto, ignorando pastas desnecessárias.
import os

def read_project_files(directory_path: str) -> str:
    """
    Recursively reads all text files in a directory.
    Ignores .git, __pycache__, node_modules, venv, .env, and binary files.
    Returns a single string with all file contents.
    """
    print(f"  [Tool] Reading files from: {directory_path}")
    
    if not os.path.exists(directory_path):
        return f"Error: Directory '{directory_path}' does not exist."

    all_content = []
    
    ignore_dirs = {'.git', '__pycache__', 'node_modules', 'venv', '.venv', 'dist', 'build', '.idea', '.vscode'}
    ignore_extensions = {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.bin', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.zip', '.tar', '.gz'}

    for root, dirs, files in os.walk(directory_path):
        # Filtra diretórios no local
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in ignore_extensions:
                continue
                
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, directory_path)
            
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Skip empty files or very large files (simple heuristic)
                    if not content.strip():
                        continue
                    if len(content) > 100000: # Pula arquivos enormes > 100KB para economizar contexto
                        content = content[:2000] + "\n... [File truncated due to size] ..."
                        
                    all_content.append(f"--- File: {rel_path} ---\n{content}\n")
            except Exception as e:
                print(f"Skipping file {rel_path}: {e}")

    result = "\n".join(all_content)
    if not result:
        return "No readable text files found in the directory."
        
    return result
