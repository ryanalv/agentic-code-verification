import sys
import os
import logging

# Adiciona o diretório raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import src.config.settings # Carrega variáveis de ambiente (.env)
from src.core.workflow import AgentWorkflow
from src.utils.logger import logger

# Configura logger para ver output no console
logging.basicConfig(level=logging.INFO)

def test_graph():
    project_path = os.path.abspath("src/agents")
    query = "Explique como os agentes são estruturados e quais são suas responsabilidades."
    
    print(f"--- Iniciando Teste do Grafo ---")
    print(f"Diretório: {project_path}")
    print(f"Query: {query}")
    
    workflow = AgentWorkflow(max_iterations=1) # 1 iteração para ser rápido
    result = workflow.run(project_path, query)
    
    print("\n\n=== RESULTADO FINAL ===")
    print(result.get("final_response", "Sem resposta final"))
    
    print("\n\n=== PASSOS ===")
    for step in result.get("steps", []):
        print(f"- {step}")
        
    print("\n\n=== ERROS ===")
    for error in result.get("errors", []):
        print(f"- {error}")

if __name__ == "__main__":
    test_graph()
