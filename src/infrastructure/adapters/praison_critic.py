# Implementação do Adapter para PraisonAI
from typing import List, Dict, Any
import os
import json
import re
from praisonai import PraisonAI
from praisonaiagents import Agent, Task
from langchain.tools import tool
from src.utils.logger import logger
from src.utils.text_splitter import split_markdown_by_headers
from src.core.ports.critic_port import ICriticAgent
from typing import List, Dict, Any
import os
import json
import re
from praisonaiagents import Agent, Task, AgentTeam
from langchain.tools import tool
from src.utils.logger import logger
from src.utils.text_splitter import split_markdown_by_headers
from src.core.ports.critic_port import ICriticAgent
from src.core.domain.entities import ReviewResult
def check_files_existence(file_paths: List[str], project_path: str) -> List[str]:
    """
    Verifica se arquivos existem no disco.
    Retorna lista de arquivos não encontrados (alucinações).
    """
    missing_files = []
    
    # Tratamento robusto de input (pode vir como string JSON ou lista)
    if isinstance(file_paths, str):
        try: file_paths = json.loads(file_paths)
        except: file_paths = [file_paths]
    
    if not isinstance(file_paths, list): file_paths = [str(file_paths)]

    for file_ref in file_paths:
        # Normalização de caminhos (Win/Unix) e remoção de sujeira (backticks)
        normalized_ref = str(file_ref).replace('/', os.sep).replace('\\', os.sep).replace('`', '').strip()
        
        if normalized_ref.startswith(os.sep): 
            normalized_ref = normalized_ref[1:]
            
        full_path = os.path.join(project_path, normalized_ref)
        
        if not os.path.exists(full_path):
            # Tenta verificar em src/ também caso o caminho seja relativo à raiz
            src_path = os.path.join(project_path, 'src', normalized_ref)
            if not os.path.exists(src_path): 
                missing_files.append(file_ref)
                
    return missing_files

class PraisonCriticAdapter(ICriticAgent):
    """
    Adapter que implementa a interface ICriticAgent usando a biblioteca PraisonAI (Hierárquica).
    """
    
    def __init__(self, worker_model="openai/gpt-4o-mini", manager_model="openai/gpt-4o"):
        # Configuração automática para OpenRouter se disponível
        if not os.getenv("OPENAI_API_KEY") and os.getenv("OPENROUTER_API_KEY"):
            os.environ["OPENAI_API_KEY"] = os.getenv("OPENROUTER_API_KEY")
            os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
            logger.info("Configurado OpenRouter como provedor LLM para PraisonAI.")

        self.worker_model = worker_model
        self.manager_model = manager_model
        logger.info("Adapter PraisonCritic inicializado.")

    def review(self, documentation: str, project_path: str) -> ReviewResult:
        """
        Executa a revisão hierárquica usando PraisonAI.
        """
        logger.info("Adapter: Iniciando revisão hierárquica via PraisonAI...")
        
        # 1. Agente Crítico de Seção (Section Critic)
        section_critic = Agent(
            role="Section Critic",
            goal="Analyze each section of the documentation for technical accuracy and clarity.",
            backstory="You are an expert technical writer and software architect. You review documentation sections.",
            llm=self.worker_model,
            tools=[check_files_existence] # Re-adding tool as it's crucial for hallucination check
        )

        # 2. Agente Crítico Líder (Lead Critic)
        lead_critic = Agent(
            role="Lead Critic",
            goal="Consolidate feedback and provide a final pass/fail score.",
            backstory="You are the lead architect. You review the feedback from Section Critic and decide if the documentation is approved.",
            llm=self.manager_model,
            instructions=f"""
            Review the feedback provided.
            1. Calculate an overall score (0-10) based on the quality and accuracy of the documentation.
            2. Identify all unique missing files (hallucinations) reported by the Section Critic.
            3. If there are any hallucinations or the overall score is less than 7.0, the documentation is NOT approved.
            4. Provide detailed feedback on areas for improvement and specific quality issues.
            
            Output a FINAL JSON object with the following structure:
            {{
                "approved": bool,
                "score": float,
                "feedback": "detailed feedback string",
                "hallucinations": ["list of unique missing files"],
                "quality_feedback": "specific quality issues feedback string"
            }}
            Ensure all keys are double-quoted. Do not use markdown code blocks for the final JSON.
            """
        )

        # 3. Criação de Tarefas Dinâmicas
        tasks = []
        sections = split_markdown_by_headers(documentation)
        if not sections:
            return ReviewResult(approved=False, score=0, feedback="Documentação vazia ou inválida.", hallucinations=[])

        section_outputs = []
        for title, content in sections.items():
            if len(content) < 50: continue # Pula seções muito curtas
            
            task = Task(
                description=f"""
                REVISAR SEÇÃO '{title}':
                
                CONTEÚDO:
                {content[:15000]}
                
                TAREFA:
                1. Identificar arquivos citados.
                2. Usar ferramenta 'check_files_existence' com project_path='{project_path}'.
                3. Avaliar qualidade (0-10).
                
                SAÍDA ESPERADA: JSON com {{ "section": "{title}", "score": number, "missing_files": [] }}
                """,
                expected_output="Resumo JSON da seção",
                agent=section_critic
            )
            tasks.append(task)
            section_outputs.append(task) # Collect outputs for context

        # Tarefa de Consolidação
        consolidation_task = Task(
            description="""
            Ler todos os relatórios das seções.
            1. Calcular média global.
            2. Listar TODAS alucinações únicas.
            3. Se houver alucinação ou nota < 7, approved = False.
            
            SAÍDA FINAL: JSON único com:
            {{ "approved": bool, "score": float, "feedback": "str", "hallucinations": [], "quality_feedback": "str" }}
            """,
            expected_output="Objeto JSON final com o veredito",
            agent=lead_critic,
            context=tasks
        )
        tasks.append(consolidation_task)
        try:
            # 4. Execução da Orquestração
            # Em v4, usamos AgentTeam para execução programática
            team = AgentTeam(
                agents=[section_critic, lead_critic],
                tasks=tasks,
                process="sequential",
                output="verbose"
            )
            
            result_raw = team.start()
            
            # Verificar falha na execução
            if isinstance(result_raw, dict) and 'task_results' in result_raw:
                # Se as tarefas não foram concluídas, result_raw é o dicionário de status
                results = result_raw.get('task_results', {})
                # Se algum status de tarefa não for None/Completed, ou results forem None
                if all(v is None for v in results.values()):
                    logger.error(f"Falha na Execução do PraisonAI. Tarefas não concluídas. Status: {result_raw.get('task_status')}")
                    return ReviewResult(approved=False, score=0, feedback=f"Falha na Execução: Agentes não retornaram resultados. Status: {result_raw.get('task_status')}", hallucinations=[])

            clean_result = str(result_raw).replace("```json", "").replace("```", "").strip()
            
            # Tenta encontrar o JSON final na string (pode vir sujo com texto do agente)
            
            json_match = re.search(r'\{.*\}', clean_result, re.DOTALL)
            data = {}
            
            if json_match:
                json_str = json_match.group(0)
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError:
                    # Fallback para aspas simples ou formato Python
                    try:
                        data = ast.literal_eval(json_str)
                    except Exception:
                         # Última tentativa: limpar preâmbulo que não seja JSON
                        logger.warning(f"Falha ao parsear JSON direto: {json_str[:100]}... Tentando correção.")
                        pass

            # Se falhou, tenta parsear o raw string direto
            if not data:
                 try:
                    data = json.loads(clean_result)
                 except:
                    try:
                        data = ast.literal_eval(clean_result)
                    except:
                        pass
            
            if data:
                return ReviewResult(
                    approved=data.get('score', 0) >= 8.0, # Critério de aprovação
                    score=data.get('score', 0),
                    feedback=data.get('feedback', ''),
                    hallucinations=data.get('hallucinations', []),
                    quality_feedback=data.get('quality_feedback', '')
                )
            else:
                logger.error(f"Falha ao parsear JSON do PraisonAI. Raw: {clean_result[:200]}")
                return ReviewResult(approved=False, score=0, feedback=f"Erro de Parse JSON Praison. Raw: {clean_result}", hallucinations=[])
                
        except Exception as e:
            logger.error(f"Exceção no Adapter PraisonAI: {e}")
            return ReviewResult(approved=False, score=0, feedback=str(e), hallucinations=[])
