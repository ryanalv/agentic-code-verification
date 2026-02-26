import os
from src.utils.rag_tools import ProjectRAG

def test_rag_utility():
    # Caminhos temporários para teste
    project_test_dir = "./tests/test_data/project"
    domain_test_dir = "./tests/test_data/domain"
    
    os.makedirs(project_test_dir, exist_ok=True)
    os.makedirs(domain_test_dir, exist_ok=True)
    
    with open(f"{project_test_dir}/app.py", "w", encoding="utf-8") as f:
        f.write("def calculate_tax():\n    return 0.15\n")
        
    with open(f"{domain_test_dir}/regras_negocio.md", "w", encoding="utf-8") as f:
        f.write("# Regras de Negócio\nA taxa de imposto padrão do sistema é de 15% para transações financeiras locais.\n")
        
    print("Arquivos de teste criados.")
    
    rag = ProjectRAG(persist_directory="./tests/.chroma_test_db")
    print("Construindo índice RAG...")
    rag.build_index(project_test_dir, domain_test_dir)
    
    print("\nExecutando Query de Teste: 'Qual a taxa de imposto e qual arquivo a calcula?'")
    result = rag.query("Qual a taxa de imposto e qual arquivo a calcula?", k=2)
    print("\n--- RESULTADO DA QUERY ---")
    print(result)
    
if __name__ == "__main__":
    test_rag_utility()
