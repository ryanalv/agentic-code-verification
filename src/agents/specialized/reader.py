from src.core.state import AgentState
from src.utils.file_tools import read_specific_file
from src.utils.logger import logger
import os

def reader_node(state: AgentState) -> AgentState:
    """
    Agente Reader: Lê os arquivos listados no plano de leitura.
    Acumula o conteúdo no estado.
    """
    logger.info("--- Reader Node: Lendo arquivos selecionados ---")
    
    plan = state.get("reading_plan", [])
    project_path = state.get("project_path", "")
    
    if not plan:
        state["files_context"] = "Nenhum arquivo foi selecionado para leitura."
        state["steps"].append("Reader: Nenhum arquivo para ler.")
        return state
        
    context_parts = []
    
    for relative_path in plan:
        try:
            full_path = os.path.join(project_path, relative_path)
            content = read_specific_file(full_path)
            
            # Formata o contexto para o LLM
            context_parts.append(f"=== CLASSE/ARQUIVO: {relative_path} ===\n{content}\n")
            logger.info(f"Lido: {relative_path}")
            
        except Exception as e:
            error_msg = f"Erro ao ler {relative_path}: {str(e)}"
            logger.error(error_msg)
            state["errors"].append(error_msg)
            
    state["files_context"] = "\n".join(context_parts)
    state["steps"].append(f"Reader: Lido {len(context_parts)} arquivos.")
    
    return state
