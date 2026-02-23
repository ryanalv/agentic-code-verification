from src.core.state import AgentState
from src.agents.specialized.scanner import scanner_node
from src.agents.specialized.planner import planner_node
from src.agents.specialized.reader import reader_node
from src.agents.specialized.writer import writer_node
from src.agents.critic import CriticAgent
from src.utils.logger import logger

class AgentWorkflow:
    """
    Orquestrador de Agentes (State Machine).
    Controla o fluxo de execução entre os agentes especializados.
    """
    def __init__(self, max_iterations: int = 3):
        self.max_iterations = max_iterations
        self.critic_agent = CriticAgent()
        
    def run(self, project_path: str, user_query: str) -> dict:
        # 1. Inicializa o Estado
        state: AgentState = {
            "project_path": project_path,
            "user_query": user_query,
            "file_structure": None,
            "files_context": None,
            "reading_plan": [],
            "draft_response": None,
            "critique_feedback": None,
            "final_response": None,
            "iteration": 0,
            "steps": [],
            "errors": []
        }
        
        logger.info(f"=== Iniciando Workflow Agêntico para: {project_path} ===")
        
        # 2. Execução Sequencial (Scanner -> Planner -> Reader)
        state = scanner_node(state)
        state = planner_node(state)
        state = reader_node(state)
        
        # 3. Loop de Refinamento (Writer <-> Critic)
        while state["iteration"] < self.max_iterations:
            logger.info(f"--- Iteração {state['iteration'] + 1}/{self.max_iterations} ---")
            
            # Writer gera o rascunho
            state = writer_node(state)
            
            # Critic valida
            draft = state.get("draft_response", "")
            if not draft or "Erro" in draft:
                logger.warning("Rascunho inválido, parando.")
                break
                
            review = self.critic_agent.review(draft, project_path)
            
            if review.get("approved"):
                logger.info(">>> Documentação APROVADA pelo Crítico! <<<")
                state["final_response"] = draft
                state["steps"].append("Critic: Aprovado.")
                return state
            else:
                logger.info(f">>> Documentação REPROVADA. Score: {review.get('score')} <<<")
                feedback = review.get("feedback", "Sem feedback.")
                hallucinations = review.get("hallucinations", [])
                
                state["critique_feedback"] = f"CRÍTICA: {feedback}\nALUCINAÇÕES DETECTADAS: {hallucinations}"
                state["steps"].append(f"Critic: Reprovado na iteração {state['iteration']}. Feedback anexado.")
                state["iteration"] += 1
                
        # Se esgotou as tentativas, retorna o último rascunho com aviso
        if not state["final_response"]:
             logger.warning("Número máximo de iterações atingido.")
             state["final_response"] = state.get("draft_response") + "\n\n(Aviso: Esta documentação atingiu o limite de refinamentos e pode conter imprecisões.)"
             
        return state
