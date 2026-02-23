from src.core.state import AgentState
from src.utils.file_tools import list_project_structure
from src.utils.logger import logger

def scanner_node(state: AgentState) -> AgentState:
    """
    Agente Scanner: Responsável por mapear a estrutura do projeto.
    Não usa LLM, apenas ferramenta determinística para velocidade.
    """
    logger.info("--- Scanner Node: Mapeando estrutura do projeto ---")
    
    project_path = state["project_path"]
    
    try:
        structure = list_project_structure(project_path)
        state["file_structure"] = structure
        state["steps"].append("Scanner: Estrutura mapeada com sucesso.")
    except Exception as e:
        error_msg = f"Erro no Scanner: {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["file_structure"] = f"Erro ao listar estrutura: {str(e)}"
        
    return state
