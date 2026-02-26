from src.agents.react_core import ReActAgent
from src.utils.logger import logger
import json

class RecursiveAgent(ReActAgent):
    """
    Agente Recursivo (RLM) capaz de delegar tarefas para sub-agentes (clones de si mesmo).
    Baseado na arquitetura RLM onde o agente gerencia seu próprio contexto e pode
    dividir problemas complexos em sub-problemas hierárquicos.
    """
    def __init__(self, tools=None, model="moonshotai/kimi-k2.5", depth=0, max_depth=3):
        super().__init__(tools, model)
        self.depth = depth
        self.max_depth = max_depth
        # Adiciona a ferramenta de delegação se ainda não atingiu a profundidade máxima
        if depth < max_depth:
            self.tools["delegate_task"] = self.delegate_task

    def delegate_task(self, task_description: str, context_path: str) -> str:
        """
        Dêlega uma subtarefa para um novo agente (Filho) focado em um contexto específico.
        
        Args:
           task_description: O que o agente filho deve fazer (ex: "Analise a classe User em models.py").
           context_path: O diretório ou arquivo que será o "Mundo Inteiro" do agente filho.
        
        Returns:
            O resultado da análise do filho (string).
        """
        logger.info(f"Prob. {self.depth} -> Delegando tarefa: '{task_description}' em '{context_path}'")
        
        # Cria um filho (Clone) com profundidade incrementada
        child_agent = RecursiveAgent(
            tools=self.tools,  # Herda as ferramentas do pai (incluindo capacidade de delegar!)
            model=self.model_name,
            depth=self.depth + 1,
            max_depth=self.max_depth
        )
        
        # O filho recebe apenas o contexto restrito
        child_goal = f"""
        Você é um Sub-Agente Especialista focado APENAS no contexto: {context_path}.
        Sua tarefa é OBJETIVA: {task_description}
        
        Não tente analisar nada fora de {context_path}.
        Seja conciso e técnico.
        """
        
        try:
            # Executa o filho
            result = child_agent.run(child_goal)
            
            # Formata o retorno
            final_answer = result.get("final_answer", "")
            if isinstance(final_answer, (dict, list)):
                return json.dumps(final_answer, indent=2, ensure_ascii=False)
            return str(final_answer)
            
        except Exception as e:
            return f"Erro na delegação para {context_path}: {str(e)}"
