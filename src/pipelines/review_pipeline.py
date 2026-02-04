from typing import Dict, Any
from src.infrastructure.adapters.praison_critic import PraisonCriticAdapter
from src.core.use_cases.verify_docs import VerifyDocumentationUseCase
from src.utils.logger import logger
from dataclasses import asdict

class ReviewPipeline:
    def __init__(self):
        # Composition Root (Ponto de Injeção de Dependência)
        # Instanciamos o Adapter concreto
        adapter = PraisonCriticAdapter()
        
        # Injetamos o Adapter no Caso de Uso
        self.use_case = VerifyDocumentationUseCase(critic_agent=adapter)
        
        logger.info("ReviewPipeline (Hexagonal) Inicializada.")

    def run(self, analyst_output: str, project_path: str) -> Dict[str, Any]:
        """
        Executa a pipeline (agora via Caso de Uso).
        """
        # Executa o Caso de Uso Puro
        domain_result = self.use_case.execute(analyst_output, project_path)
        
        # Converte o resultado de Domínio (DataClass) para Dicionário (para manter compatibilidade)
        return asdict(domain_result)
