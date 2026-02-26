# Definição do Estado Compartilhado para o Grafo de Agentes
# Este estado flui entre todos os agentes especializados (Scanner, Planner, Reader, Writer, Critic)

from typing import TypedDict, List, Optional, Any, Dict

class AgentState(TypedDict):
    """
    Estado compartilhado que flui através do grafo de agentes.
    Baseado no padrão recomendado por LangGraph/StateGraph.
    """
    project_path: str
    user_query: str
    
    # --- Contexto do Projeto ---
    domain_knowledge_path: Optional[str] # Caminho opcional para conhecimentos de domínio adicionais
    file_structure: Optional[str]      # Saída do Scanner: Mapa do projeto
    files_context: Optional[str]       # Saída do Reader: Conteúdo lido dos arquivos completos
    rag_context: Optional[str]         # Contexto recuperado pelo sistema RAG
    
    # --- Planejamento ---
    reading_plan: Optional[List[str]]  # Saída do Planner: Lista de arquivos a ler
    
    # --- Saídas ---
    draft_response: Optional[str]      # Saída do Writer: Rascunho da documentação
    critique_feedback: Optional[str]   # Saída do Critic: Feedback sobre o rascunho
    final_response: Optional[str]      # Resposta aprovada final
    
    # --- Metadados de Execução ---
    iteration: int                     # Contador de loops de correção
    steps: List[str]                   # Log de passos executados para debug
    errors: List[str]                  # Lista de erros encontrados durante o processo
