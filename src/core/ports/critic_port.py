from abc import ABC, abstractmethod
from typing import Dict, Any
from src.core.domain.entities import ReviewResult

class ICriticAgent(ABC):
    """Porta (Interface) para o Agente Crítico."""
    
    @abstractmethod
    def review(self, analyst_output: str, project_path: str) -> ReviewResult:
        """
        Executa a revisão da documentação.
        Deve ser implementada por um Adapter (ex: praison_critic).
        
        Args:
            analyst_output: O texto markdown da documentação.
            project_path: Caminho raiz do projeto para validação.
            
        Returns:
            ReviewResult: Entidade de domínio com o veredito.
        """
        pass
