import os
import sys
import time
import pandas as pd

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..')
sys.path.append(src_path)

from src.code_analyst import analyze_codebase
from src.agents.critic import CriticAgent

# Project Path (The project itself)
PROJECT_PATH = os.path.join(src_path, "src")
PROJECT_NAME = "AI Quality Critic Agent"

    # Mock Critic para testes quando API key está faltando
class MockCritic:
    def review(self, text, path):
         return {} # Será sobrescrito no loop manualmente ou podemos colocar lógica aqui

def run_analysis_loop(max_retries=2):
    # Verificação de MOCK
    use_mock = os.getenv("OPENROUTER_API_KEY") is None
    
    if use_mock:
        print("AVISO: API Key não encontrada. Usando Crítico MOCKADO para verificação.")
        critic = MockCritic()
    else:
        critic = CriticAgent()
    
    history = []
    
    current_feedback = None
    
    print(f"Iniciando Análise em {PROJECT_PATH}...")
    
    # MOCK BEHAVIOR for Demonstration/Testing without API Key
    use_mock = os.getenv("OPENROUTER_API_KEY") is None
    if use_mock:
        print("AVISO: API Key não encontrada. Usando respostas MOCKADAS para lógica de verificação.")

    for i in range(max_retries + 1):
        print(f"\n--- Iteração {i} ---")
        start_time = time.time()
        
        # 1. Executar Analista
        print("Executando Code Analyst...")
        if use_mock:
            # Comportamento Mock: Primeira execução ruim, segunda boa
            if i == 0:
                doc_text = "Aqui está o doc. Refere-se a `src/non_existent_file.py` e `README.md`."
                steps = 5
                usage = {"total_tokens": 500}
            else:
                doc_text = "Aqui está o doc corrigido. Refere-se a `src/code_analyst.py` e `README.md`."
                steps = 6
                usage = {"total_tokens": 600}
            analyst_result = {"final_answer": doc_text, "steps": steps, "usage": usage}
            time.sleep(1)
        else:
            try:
                analyst_result = analyze_codebase(PROJECT_PATH, PROJECT_NAME, feedback=current_feedback)
            except Exception as e:
                print(f"Analista falhou: {e}")
                break
            
        doc_text = analyst_result.get("final_answer", "")
        if not doc_text:
            print("Analista retornou texto vazio.")
            break
            
        usage = analyst_result.get("usage", {})
        steps = analyst_result.get("steps", 0)
        
        # 2. Executar Crítico
        print("Executando Agente Crítico...")
        if use_mock and i == 0:
            # Primeira iteração: Força alucinação
             review_result = {
                "approved": False,
                "score": 5,
                "feedback": "Alucinação detectada.",
                "hallucinations": ["src/non_existent_file.py"],
                "quality_feedback": "Por favor corrija os caminhos dos arquivos."
            }
        elif use_mock: 
             # Segunda iteração: Passa
             review_result = {
                "approved": True,
                "score": 9,
                "feedback": "",
                "hallucinations": [],
                "quality_feedback": "Bom trabalho."
            }
        else:
            review_result = critic.review(doc_text, PROJECT_PATH)
            # Log extra para debug
            print(f"Debug Critic Output: {review_result}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Registrar Métricas
        metrics = {
            "iteration": i,
            "duration_sec": round(duration, 2),
            "analyst_steps": steps,
            "quality_score": review_result["score"],
            "hallucinations": len(review_result["hallucinations"]),
            "approved": review_result["approved"]
        }
        history.append(metrics)
        
        print(f"Resultado: Aprovado={review_result['approved']} | Score={review_result['score']} | Alucinações={len(review_result['hallucinations'])}")
        
        if review_result['approved']:
            print("Documentação Aprovada!")
            break
        else:
            current_feedback = review_result["feedback"]
            print(f"Feedback: {current_feedback[:100]}...")
    
    print("\n--- Métricas Finais ---")
    print(pd.DataFrame(history))

if __name__ == "__main__":
    run_analysis_loop()
