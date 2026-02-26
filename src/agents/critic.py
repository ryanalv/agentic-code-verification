# critic.py - Agente responsável por revisar a documentação gerada e verificar alucinações.
# Refatorado para usar Arquitetura Hierárquica (Map-Reduce) com PraisonAI
from typing import Dict, List, Any, Optional
import os
import json
import re
import re
from praisonaiagents import Agent, Task, AgentTeam
from langchain.tools import tool
from src.utils.logger import logger
from src.utils.text_splitter import split_markdown_by_headers

# Ferramenta para verificação de arquivos
@tool("check_files_existence")
def check_files_existence(file_paths: List[str], project_path: str) -> List[str]:
    """
    Verifica se uma lista de caminhos de arquivos existe dentro do diretório do projeto.
    Retorna uma lista dos arquivos que NÃO foram encontrados (alucinações).
    """
    missing_files = []
    
    # Normalização de input robusta
    if isinstance(file_paths, str):
        try:
             file_paths = json.loads(file_paths)
        except:
             if ',' in file_paths:
                 file_paths = [x.strip() for x in file_paths.split(',')]
             else:
                 file_paths = [file_paths]
    
    # Se ainda não for lista, encapsula
    if not isinstance(file_paths, list):
        file_paths = [str(file_paths)]

    for file_ref in file_paths:
        # Normaliza separadores
        normalized_ref = str(file_ref).replace('/', os.sep).replace('\\', os.sep)
        # Remove caracteres indesejados comuns (ex: backticks)
        normalized_ref = normalized_ref.replace('`', '').strip()
        
        if normalized_ref.startswith(os.sep):
            normalized_ref = normalized_ref[1:]
            
        full_path = os.path.join(project_path, normalized_ref)
        
        if not os.path.exists(full_path):
            # Tenta verificar em src/ também
            src_path = os.path.join(project_path, 'src', normalized_ref)
            if not os.path.exists(src_path):
                 missing_files.append(file_ref)
    
    return missing_files

class CriticAgent:
    def __init__(self):
        # Configuração automática para OpenRouter se disponível
        if not os.getenv("OPENAI_API_KEY") and os.getenv("OPENROUTER_API_KEY"):
            os.environ["OPENAI_API_KEY"] = os.getenv("OPENROUTER_API_KEY")
            os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
            
        # Modelos configuráveis via ENV ou hardcoded para este exemplo
        self.worker_model = "openai/gpt-5.1" # Rápido e barato para leitura de volume
        self.manager_model = "moonshotai/kimi-k2.5"     # Inteligente para decisão final
        logger.info("CriticAgent Hierárquico (PraisonAI) inicializado.")

    def review(self, analyst_output: str, project_path: str) -> Dict[str, Any]:
        """
        Orquestra o processo de revisão hierárquica.
        1. Fatia a documentação (Map)
        2. Analisa cada seção em paralelo/sequencial (Process)
        3. Consolida os resultados (Reduce)
        """
        logger.info("Iniciando revisão hierárquica...")
        

        # 1. Split da Documentação
        sections = split_markdown_by_headers(analyst_output)
        logger.info(f"Documentação dividida em {len(sections)} seções para análise.")
        
        if not sections:
            return {"approved": False, "score": 0, "feedback": "Documentação vazia ou inválida.", "hallucinations": []}

        # 2. Definição dos Agentes
        
        # Agente Especialista (Worker)
        section_critic = Agent(
            role="Revisor Técnico de Seção",
            goal="Verificar a existência de arquivos e a profundidade técnica de uma seção específica da documentação.",
            backstory="Você é um revisor de código meticuloso. Você recebe uma seção de um documento e deve verificar se cada arquivo mencionado realmente existe usando sua ferramenta. Você é estritamente técnico.",
            tools=[check_files_existence],
            llm=self.worker_model
        )

        # Agente Líder (Manager)
        lead_critic = Agent(
            role="Arquiteto Líder de Documentação",
            goal="Consolidar revisões de seções em um veredito final.",
            backstory="Você é o Gerente de Release. Você lê os relatórios de análise de sua equipe e decide se a documentação é boa o suficiente para ser publicada. Você é rigoroso com alucinações (arquivos inexistentes).",
            llm=self.manager_model
        )

        # 3. Criação Dinâmica de Tarefas (Tasks)
        tasks = []
        
        # Para cada seção, cria uma tarefa de revisão
        for title, content in sections.items():
            # Pula seções muito pequenas/vazias
            if len(content) < 50: 
                continue
                
            task_desc = f"""
            REVISAR SEÇÃO: '{title}'
            
            CONTEÚDO:
            {content[:15000]} 
            
            SEU TRABALHO:
            1. Identificar TODOS os caminhos de arquivos mencionados nesta seção (procure em blocos de código, crases, comentários).
            2. Executar a ferramenta 'check_files_existence' com project_path='{project_path}' e a lista de arquivos.
            3. Avaliar a Clareza e Completude desta seção (0-10).
            
            SAÍDA:
            Retorne um resumo JSON com:
            {{ "section": "{title}", "score": number, "missing_files": ["list"] }}
            """
            
            task = Task(
                description=task_desc,
                expected_output="Resumo JSON da revisão da seção",
                agent=section_critic
            )
            tasks.append(task)
            
        # Tarefa de Consolidação (Reduce)
        consolidation_desc = f"""
        Você recebeu relatórios de sua equipe sobre as seções da documentação.
        
        SEU TRABALHO:
        1. Calcular a pontuação média global (0-10).
        2. Compilar uma LISTA MESTRA de TODOS os arquivos ausentes únicos (alucinações) relatados por sua equipe.
        3. Escrever um texto de feedback final resumindo a qualidade da documentação.
        
        CRITÉRIOS:
        - Se houver QUALQUER arquivo ausente (alucinação), o status 'approved' DEVE ser False.
        - Se a pontuação global for inferior a 7.0, 'approved' DEVE ser False.
        
        FORMATO DE SAÍDA FINAL:
        Retorne um ÚNICO objeto JSON válido (sem markdown):
        {{
            "approved": boolean,
            "score": number, 
            "feedback": "string",
            "hallucinations": ["lista", "de", "todos", "arquivos", "ausentes"],
            "quality_feedback": "feedback técnico detalhado"
        }}
        """
        
        consolidation_task = Task(
            description=consolidation_desc,
            expected_output="Objeto JSON final com o veredito",
            agent=lead_critic,
            context=tasks # Recebe o output de todas as tarefas anteriores
        )
        tasks.append(consolidation_task)

        # 4. Execução PraisonAI
        team = AgentTeam(
            agents=[section_critic, lead_critic],
            tasks=tasks,
            process="sequential"
        )
        
        try:
            result_raw = team.start()
            logger.debug(f"PraisonAI raw result: {result_raw}")
            
            # Parsing do Resultado Final
            clean_result = str(result_raw).replace("```json", "").replace("```", "").strip()
            
            # Tenta encontrar o JSON final na string (pode vir sujo com texto do agente)
            json_match = re.search(r'\{.*\}', clean_result, re.DOTALL)
            if json_match:
                result_json = json.loads(json_match.group(0))
            else:
                # Fallback se não achar JSON
                logger.error("Falha ao parsear JSON final do PraisonAI")
                return {
                    "approved": False,
                    "score": 0,
                    "feedback": "Erro: Agente não retornou JSON válido.",
                    "hallucinations": [],
                    "quality_feedback": str(clean_result)
                }
            
            return result_json

        except Exception as e:
            logger.error(f"Erro na execução hierárquica: {e}")
            return {
                "approved": False,
                "score": 0,
                "feedback": f"Exception na pipeline: {e}",
                "hallucinations": [],
            }