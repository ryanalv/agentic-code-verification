from src.core.ports.critic_port import ICriticAgent
from src.core.domain.entities import ReviewResult
from src.utils.logger import logger

class VerifyDocumentationUseCase:
    """
    Caso de Uso: Verificar Documentação Técnica.
    Responsável por orquestrar a lógica de negócio da validação de documentos,
    independente de qual IA está sendo usada.
    """
    
    def __init__(self, critic_agent: ICriticAgent):
        # Injeção de Dependência: O Caso de Uso não sabe que é PraisonAI.
        # Ele só conhece a Interface ICriticAgent.
        self.critic = critic_agent

    def execute(self, analyst_output: str, project_path: str) -> ReviewResult:
        logger.info("Iniciando Caso de Uso: Verificar Documentação...")
        
        # Executa a lógica de negócio através da porta
        result = self.critic.review(analyst_output, project_path)
        
        logger.info(f"Caso de Uso Finalizado. Aprovado: {result.approved}, Nota: {result.score}")
        return result
