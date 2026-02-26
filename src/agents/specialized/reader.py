from src.core.state import AgentState
from src.utils.file_tools import read_specific_file
from src.utils.rag_tools import ProjectRAG
from src.utils.logger import logger
import os

def reader_node(state: AgentState) -> AgentState:
    """
    Agente Reader: Constrói o índice RAG (se necessário) e busca o contexto
    relevante para a query do usuário. Também lê arquivos especificados no plano.
    """
    logger.info("--- Reader Node: Processando RAG e leitura de arquivos ---")
    
    plan = state.get("reading_plan", [])
    project_path = state.get("project_path", "")
    domain_knowledge_path = state.get("domain_knowledge_path")
    user_query = state.get("user_query", "")
    
    # 1. Recuperação via RAG
    try:
        rag = ProjectRAG()
        rag.build_index(project_path, domain_knowledge_path)
        # Usa a query original (ou o plano) para buscar pedaços relevantes
        # Se pudermos deduzir uma query melhor a partir do plano, o faríamos,
        # mas por enquanto usamos a user_query.
        search_query = user_query + " " + " ".join(plan)
        rag_context = rag.query(search_query, k=10)
        state["rag_context"] = rag_context
        state["steps"].append("Reader: Contexto RAG recuperado com sucesso.")
        logger.info("Contexto RAG recuperado")
    except Exception as e:
        error_msg = f"Erro ao processar RAG: {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["rag_context"] = f"Erro no RAG: {e}"

    # 2. Leitura Direta (Leitura completa dos arquivos planejados)
    if not plan:
        state["files_context"] = "Nenhum arquivo listado para leitura integral."
        state["steps"].append("Reader: Sem arquivos para leitura integral.")
        return state
        
    context_parts = []
    
    for relative_path in plan:
        try:
            full_path = os.path.join(project_path, relative_path)
            content = read_specific_file(full_path)
            
            # Formata o contexto para o LLM
            context_parts.append(f"=== CLASSE/ARQUIVO (LEITURA INTEGRAL): {relative_path} ===\n{content}\n")
            logger.info(f"Lido integralmente: {relative_path}")
            
        except Exception as e:
            error_msg = f"Erro ao ler integralmente {relative_path}: {str(e)}"
            logger.error(error_msg)
            state["errors"].append(error_msg)
            
    state["files_context"] = "\n".join(context_parts)
    state["steps"].append(f"Reader: Lido {len(context_parts)} arquivos completamente.")
    
    return state
