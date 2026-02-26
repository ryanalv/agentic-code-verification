# code_analyst.py - Orquestrador principal de análise de código.
# Utiliza os agentes do sistema para analisar a base de código e gerar documentação técnica.
from src.agents.react_core import ReActAgent
from src.agents.recursive_agent import RecursiveAgent
from src.utils.file_tools import read_project_files, list_project_structure, read_specific_file, count_project_files
from src.tools.context_tools import list_files_in_context, run_grep_search
from src.utils.logger import logger
import os

def analyze_codebase(project_path: str, project_name: str, feedback: str = None, domain_knowledge_path: str = None) -> dict:
    """
    Analisa a base de código utilizando uma estratégia adaptativa:
    - Pequenos Projetos (<= 15 arquivos): Usa ReActAgent padrão (mais rápido, linear).
    - Grandes Projetos (> 15 arquivos): Usa RecursiveAgent (RLM) para dividir e conquistar.
    Incorpora opcionalmente conhecimento de domínio.
    """
    
    # Decisão de Estratégia
    total_files = count_project_files(project_path)
    use_recursive = True  # Forçar sempre o uso da pipeline Map-Reduce e Crítico
    
    strategy_name = "RLM (Recursivo)" if use_recursive else "ReAct (Linear)"
    logger.info(f"Iniciando análise de '{project_name}'. Arquivos: {total_files}. Estratégia: {strategy_name}")

    # Wrappers para injetar o contexto do caminho do projeto automaticamente
    def list_structure_wrapper(directory_path: str = None) -> str:
        target_path = directory_path if directory_path else project_path
        return list_project_structure(target_path)

    def read_files_wrapper(directory_path: str = None) -> str:
        target_path = directory_path if directory_path else project_path
        return read_project_files(target_path)

    def read_file_wrapper(file_path: str) -> str:
        if not file_path: return "Erro: Caminho do arquivo não fornecido."
        target_path = file_path
        if not os.path.isabs(file_path):
            target_path = os.path.join(project_path, file_path)
        return read_specific_file(target_path)

    goal = f"""
    Você é um Arquiteto de Software Sênior especializado em análise de código e documentação técnica EXAUSTIVA.
    Sua missão é realizar uma análise profunda do projeto {project_name} e gerar documentação técnica EXTREMAMENTE DETALHADA.
    
    O DIRETÓRIO DO PROJETO É: {project_path}
    
    ### REGRAS DE OURO (GOLDEN RULES):
    1. Jamais abrevie ou pule arquivos - cada componente do contexto lido deve ser extensivamente especificado.
    2. Toda a análise deve ser formal e não economizar tokens.
    3. NÃO FAÇA RESUMOS. Eu quero DETALHES TÉCNICOS detalhados de Classes, Funções e Fluxos.
    4. A documentação deve conter: Visão Geral, Tecnologias, Arquitetura, Análise de Código Detalhada e Fluxos de Dados.
    """
    
    if feedback:
        goal += f"\n\nATENÇÃO - FEEDBACK DE CRÍTICA ANTERIOR:\n{feedback}\nPor favor, corrija os pontos acima na nova documentação."

    # Configuração de Ferramentas e Agente
    if use_recursive:
        # --- ESTRATÉGIA GRAFO DE AGENTES (GEN 2) ---
        from src.core.workflow import AgentWorkflow
        
        logger.info(f"Análise Agêntica (Graph) iniciada para: {project_path}")

        workflow = AgentWorkflow(max_iterations=3)
        result_state = workflow.run(project_path, goal, domain_knowledge_path)
        
        final_doc = result_state.get("final_response", "")
        if not final_doc:
            final_doc = "Erro: Não foi possível gerar a documentação."
            
        return {
            "final_answer": final_doc,
            "steps": len(result_state.get("steps", [])),
            "details": result_state
        }
        
    else:
        # --- ESTRATÉGIA REACT PADRÃO (PROJETOS PEQUENOS) ---
        tools = {
            "read_project_files": read_files_wrapper, 
            "list_project_structure": list_structure_wrapper,
            "read_specific_file": read_file_wrapper
        }
        
        goal += """
        FERRAMENTAS:
        1. `list_project_structure`: Veja a estrutura de arquivos.
        2. `read_project_files`: Leia o conteúdo dos arquivos (Cuidado com o tamanho!).
        3. `read_specific_file`: Leia arquivos específicos.

        ### ESTRATÉGIA LINEAR:
        1. Liste a estrutura.
        2. Leia os arquivos principais.
        3. Documente detalhadamente Classes, Funções e Fluxos.
        """
        
        # Agente Linear Clássico
        agent = ReActAgent(tools=tools, model="moonshotai/kimi-k2.5")

        return agent.run(goal)
