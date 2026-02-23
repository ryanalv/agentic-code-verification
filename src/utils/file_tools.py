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
    total_chars = 0
    # Limite aproximado de c. 120k tokens
    # Reduzindo drasticamente para 150k chars (aprox 35k-50k tokens) para garantir espaço para resposta e system prompt
    MAX_TOTAL_CHARS = 150000 
    
    # Lista expandida de diretórios para ignorar
    ignore_dirs = {
        '.git', '__pycache__', 'node_modules', 'venv', '.venv', 'env', '.env', 
        'dist', 'build', '.idea', '.vscode', 'target', 'bin', 'obj', 'lib', 
        'out', 'coverage', '.mypy_cache', '.pytest_cache', 'site-packages', 'gems',
        'pkg', 'vendor', 'deploy'
    }
    
    # Lista expandida de extensões para ignorar
    ignore_extensions = {
        '.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.bin', 
        '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.bmp', '.tiff', '.webp',
        '.zip', '.tar', '.gz', '.rar', '.7z', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac',
        '.db', '.sqlite', '.sqlite3', '.parquet', '.h5', '.hdf5', '.pkl', '.iso',
        '.eot', '.woff', '.woff2', '.ttf'
    }
    
    # Arquivos de lock e outros meta-dados muito grandes que não agregam valor à análise de código
    ignore_files = {
        'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'poetry.lock', 'Cargo.lock', 'go.sum',
        'composer.lock', 'Gemfile.lock', '.env', '.env.local', '.env.development', '.env.test', '.env.production'
    }

    truncated = False

    for root, dirs, files in os.walk(directory_path):
        # Filtra diretórios no local (importante modificar a lista 'dirs' in-place)
        # Remove diretórios que começam com . (ocultos) ou estão na lista de ignorados
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
        
        for file in files:
            # Verifica limite global antes de processar
            if total_chars >= MAX_TOTAL_CHARS:
                truncated = True
                break

            if file in ignore_files:
                continue

            ext = os.path.splitext(file)[1].lower()
            if ext in ignore_extensions:
                continue
                
            filepath = os.path.join(root, file)
            # Ignora arquivos muito grandes (> 50MB) logo de cara para não travar leitura
            try:
                if os.path.getsize(filepath) > 50 * 1024 * 1024:
                    continue
            except:
                pass

            rel_path = os.path.relpath(filepath, directory_path)
            
            try:
                # Tenta ler o arquivo
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Pula arquivos vazios
                    if not content.strip():
                        continue
                        
                    # Limite por arquivo individual (hard limit para um único arquivo)
                    # 30k chars ~= 7.5k tokens por arquivo individual máximo
                    MAX_FILE_CHARS = 30000 
                    if len(content) > MAX_FILE_CHARS: 
                        content = content[:MAX_FILE_CHARS] + f"\n... [Arquivo truncado: exibindo primeiros {MAX_FILE_CHARS} caracteres de {len(content)}] ..."
                        
                    file_block = f"--- Arquivo: {rel_path} ---\n{content}\n"
                    file_len = len(file_block)

                    if total_chars + file_len > MAX_TOTAL_CHARS:
                        # Se adicionar esse arquivo estoura o limite, adiciona o que der (se for relevante) ou para
                        available = MAX_TOTAL_CHARS - total_chars
                        if available > 500: # Se ainda tem um espaço razoável
                            all_content.append(file_block[:available] + "\n... [Limite Global de Contexto Atingido] ...")
                        truncated = True
                        break
                    
                    all_content.append(file_block)
                    total_chars += file_len

            except Exception as e:
                print(f"Pulando arquivo {rel_path}: {e}")
        
        if truncated:
            break

    if truncated:
        all_content.append(f"\n\n[AVISO CRÍTICO: O projeto é muito grande. A leitura foi interrompida após ler {total_chars} caracteres para não exceder o limite de contexto do LLM (128k). Alguns arquivos não foram lidos. Se necessário, analise subdiretórios específicos.]")

    result = "\n".join(all_content)
    if not result:
        return "Nenhum arquivo de texto legível encontrado no diretório."
        
    print(f"  [Tool] Total characters read: {total_chars}. Truncated: {truncated}")
    return result

def list_project_structure(directory_path: str) -> str:
    """
    Lists the directory structure of the project, ignoring common junk folders.
    Returns a tree-like string representation.
    """
    if not os.path.exists(directory_path):
        return f"Error: Directory '{directory_path}' does not exist."

    ignore_dirs = {
        '.git', '__pycache__', 'node_modules', 'venv', '.venv', 'env', '.env', 
        'dist', 'build', '.idea', '.vscode', 'target', 'bin', 'obj', 'lib', 
        'out', 'coverage', '.mypy_cache', '.pytest_cache', 'site-packages'
    }

    structure = []
    
    for root, dirs, files in os.walk(directory_path):
        # Filter directories in-place
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
        
        level = root.replace(directory_path, '').count(os.sep)
        indent = ' ' * 4 * (level)
        structure.append(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        
        # Limit the number of files shown per directory to avoid huge lists
        MAX_FILES_PER_DIR = 50
        for i, f in enumerate(files):
            if i >= MAX_FILES_PER_DIR:
                structure.append(f"{subindent}... ({len(files) - MAX_FILES_PER_DIR} more files)")
                break
            if not f.startswith('.'): # Ignore hidden files in listing
                structure.append(f"{subindent}{f}")
                
    return "\n".join(structure)

def read_specific_file(file_path: str) -> str:
    """
    Reads a specific file from the project.
    Args:
        file_path: Absolute path or path relative to the project root.
    """
    if not os.path.exists(file_path):
        return f"Error: File '{file_path}' does not exist."
        
    if os.path.isdir(file_path):
        return f"Error: '{file_path}' is a directory. Use list_project_structure to see contents."

    try:
        if os.path.getsize(file_path) > 100 * 1024: # 100KB limit for single file
             return f"Error: File '{file_path}' is too large to read fully (>100KB). Please look for smaller, more specific files."
             
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            return f"--- File: {file_path} ---\n{content}"
    except Exception as e:
        return f"Error reading file '{file_path}': {str(e)}"

def count_project_files(directory_path: str) -> int:
    """
    Conta o número de arquivos válidos no projeto (respeitando ignores).
    Usado para decidir a estratégia do agente (Linear vs Recursivo).
    """
    if not os.path.exists(directory_path):
        return 0

    ignore_dirs = {
        '.git', '__pycache__', 'node_modules', 'venv', '.venv', 'env', '.env', 
        'dist', 'build', '.idea', '.vscode', 'target', 'bin', 'obj', 'lib', 
        'out', 'coverage', '.mypy_cache', '.pytest_cache', 'site-packages', 'gems',
        'pkg', 'vendor', 'deploy'
    }
    
    ignore_extensions = {
        '.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.bin', 
        '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.bmp', '.tiff', '.webp',
        '.zip', '.tar', '.gz', '.rar', '.7z', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac',
        '.db', '.sqlite', '.sqlite3', '.parquet', '.h5', '.hdf5', '.pkl', '.iso',
        '.eot', '.woff', '.woff2', '.ttf'
    }

    count = 0
    for root, dirs, files in os.walk(directory_path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in ignore_extensions:
                continue
            count += 1
            
    return count
