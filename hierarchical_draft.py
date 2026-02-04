# Esboço de Arquitetura Hierárquica para Projetos Grandes com PraisonAI (Hierarchical/Manager Mode)

from typing import Dict, Any, List
from praisonai import PraisonAI
from praisonai.agents import Agent
from praisonai.tasks import Task
from langchain.tools import tool
import os

# --- Ferramentas Robustas ---

@tool("check_file_paths")
def check_file_paths(file_paths: List[str], project_root: str) -> Dict[str, List[str]]:
    """
    Verifica massivamente uma lista de arquivos.
    Ideal para ser chamada pelo agente com listas extraídas de uma seção específica.
    """
    existing = []
    missing = []
    
    # Lógica de validação real
    for path in file_paths:
        full = os.path.join(project_root, path) # Simplificação
        if os.path.exists(full):
            existing.append(path)
        else:
            missing.append(path)
            
    return {"missing": missing, "count_checked": len(file_paths)}

# --- Definição dos Agentes ---

def create_hierarchical_review_squad(project_path: str, documentation_sections: Dict[str, str]):
    """
    Cria uma equipe dinâmica baseada nas seções da documentação.
    
    Args:
        project_path: Caminho raiz do projeto.
        documentation_sections: Dict onde chave é o Titulo da Seção e valor é o Conteúdo.
                                Ex: {'Auth Module': '...', 'Database': '...'}
    """
    
    # 1. Agente Especialista (Worker)
    # Este agente será clonado/instanciado para cada seção ou trabalhará em fila.
    # Em projetos GIGANTES, idealmente você processa em chunks.
    
    section_critic = Agent(
        role="Section Technical Reviewer",
        goal="Review a specific section of technical documentation for specific file accuracy and technical depth.",
        backstory="You are a specialized code reviewer. You focus only on the text provided to you. You are extremely pedantic about file paths existing.",
        tools=[check_file_paths],
        verbose=True,
        allow_delegation=False, # Ele é a ponta, não delega
        llm="gpt-4o-mini" # Modelo mais rápido/barato para os workers
    )

    # 2. Agente Líder (Manager)
    # Na PraisonAI (modo hierárquico), o manager é implícito se usarmos Process.hierarchical,
    # MAS para controle fino, definimos um Lead explícito que consolida.
    
    lead_critic = Agent(
        role="Lead Documentation Architect",
        goal="Consolidate reviews from section critics and provide a final approval verdict.",
        backstory="You are the release manager. You receive detailed reports about specific modules and decide if the whole documentation ships or fails.",
        verbose=True,
        allow_delegation=True, # Ele pode delegar dúvidas de volta ou para outros
        llm="gpt-4o" # Modelo mais forte para a decisão final
    )

    # --- Definição das Tarefas (Tasks) ---
    
    tasks = []
    
    # Para cada seção grande da documentação, criamos uma tarefa específica
    for title, content in documentation_sections.items():
        task = Task(
            description=f"""
            REVIEW SECTION: '{title}'
            
            CONTENT TO REVIEW:
            {content[:20000]} # Limite de segurança por chunk
            
            1. Extract all file paths mentioned in this section.
            2. Use 'check_file_paths' tool with project_root='{project_path}'.
            3. Rate clarity and depth of this specific section (0-10).
            
            Return a JSON summary for this section.
            """,
            expected_output="JSON with section_score and missing_files list",
            agent=section_critic # O especialista executa
        )
        tasks.append(task)

    # Tarefa final de consolidação
    consolidation_task = Task(
        description="""
        Read the outputs from all previous section reviews.
        
        1. Calculate Global Average Score.
        2. Compile a MASTER LIST of unique missing files (hallucinations) from all sections.
        3. Create a final feedback text summarizing which sections are weak.
        
        Final Output must be the standard JSON structure:
        { "approved": bool, "score": float, "hallucinations": [], "feedback": "..." }
        """,
        expected_output="Final JSON verdict",
        agent=lead_critic, # O líder executa
        context=tasks # Recebe o output de todas as tarefas anteriores
    )
    
    tasks.append(consolidation_task)

    # --- Orquestração ---
    
    # Aqui a mágica acontece. O PraisonAI gerencia a execução sequencial ou paralela (dependendo da config).
    squad = PraisonAI(
        agents=[section_critic, lead_critic],
        tasks=tasks,
        verbose=True,
        process="sequential" # Ou "hierarchical" se deixar o manager automatico
    )
    
    return squad

# Exemplo de como preparar os dados antes de chamar a squad
def split_documentation(full_text: str) -> Dict[str, str]:
    """
    Função auxiliar (não AI) que quebra o markdown gigante em capítulos.
    Isso é vital para projetos grandes. Não jogue 100k tokens direto no LLM.
    """
    sections = {}
    # Lógica simples de split por headers "# "
    current_title = "Intro"
    current_text = []
    
    for line in full_text.split('\n'):
        if line.startswith('# '):
            sections[current_title] = '\n'.join(current_text)
            current_title = line.strip()
            current_text = []
        else:
            current_text.append(line)
            
    sections[current_title] = '\n'.join(current_text)
    return sections
