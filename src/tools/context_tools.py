import os
import fnmatch

def list_files_in_context(directory: str, max_depth: int = 1) -> str:
    """
    Lista arquivos em um diretório com profundidade limitada.
    Ideal para exploração inicial antes de delegar.
    
    Args:
        directory: O diretório a ser listado.
        max_depth: Profundidade máxima da listagem (padrão 1 para visão superficial).
    """
    if not os.path.isdir(directory):
        return f"Erro: {directory} não é um diretório válido."
        
    structure = []
    base_level = directory.rstrip(os.sep).count(os.sep)
    
    for root, dirs, files in os.walk(directory):
        current_level = root.count(os.sep)
        if current_level - base_level >= max_depth:
            del dirs[:] # Para de descer
            continue
            
        indent = "  " * (current_level - base_level)
        structure.append(f"{indent}{os.path.basename(root)}/")
        
        for f in files:
            structure.append(f"{indent}  {f}")
            
    return "\n".join(structure)

def run_grep_search(query: str, path: str, context_lines: int = 2) -> str:
    """
    Busca por um padrão de texto (regex simples) dentro dos arquivos do caminho especificado.
    Simula um 'grep'. Útil para achar onde uma classe ou função é definida.
    """
    results = []
    try:
        if os.path.isfile(path):
            files_to_search = [path]
        else:
            files_to_search = []
            for root, _, files in os.walk(path):
                for f in files:
                    if f.endswith(('.py', '.md', '.txt', '.js', '.html', '.css')): # Filtro básico
                        files_to_search.append(os.path.join(root, f))
        
        count = 0
        for file_path in files_to_search:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines):
                        if query in line:
                            start = max(0, i - context_lines)
                            end = min(len(lines), i + context_lines + 1)
                            snippet = "".join(lines[start:end])
                            results.append(f"--- {file_path} (L{i+1}) ---\n{snippet}\n")
                            count += 1
                            if count >= 10: # Limite de resultados
                                return "\n".join(results) + "\n... (mais resultados truncados)"
            except:
                continue
                
        if not results:
            return f"Nenhuma ocorrência de '{query}' encontrada em {path}."
            
        return "\n".join(results)
        
    except Exception as e:
        return f"Erro na busca: {str(e)}"
