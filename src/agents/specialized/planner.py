# Agente Planner responsável por analisar a estrutura do projeto e selecionar os arquivos vitais para a documentação.
import json
import os
from openai import OpenAI
from src.core.state import AgentState
from src.utils.logger import logger

def planner_node(state: AgentState) -> AgentState:
    """
    Agente Planner: Analisa a estrutura de arquivos e a query do usuário 
    para decidir QUAIS arquivos são relevantes para leitura.
    """
    logger.info("--- Planner Node: Decidindo arquivos para leitura ---")
    
    structure = state.get("file_structure", "")
    query = state.get("user_query", "")
    
    # Se não houver estrutura, não há o que planejar
    if not structure or "Erro" in structure:
        state["reading_plan"] = []
        state["errors"].append("Planner: Estrutura inválida ou vazia.")
        return state

    # Configuração do LLM (Pode ser abstraído depois)
    from openai import AzureOpenAI
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-2").strip('"')

    client = AzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        azure_endpoint=azure_endpoint
    )
    model = deployment_name

    prompt = f"""
    Você é um Arquiteto de Software Sênior planejando uma análise de código.
    
    OBJETIVO: Identificar quais arquivos do projeto são CRITICAMENTE RELEVANTES para responder à pergunta do usuário.
    
    PERGUNTA DO USUÁRIO: "{query}"
    
    ESTRUTURA DO PROJETO:
    {structure}
    
    REGRAS:
    1. Selecione ATÉ 30 arquivos essenciais. Certifique-se de cobrir todos os componentes principais para que a documentação seja rica em detalhes.
    2. Ignore arquivos de teste, lock files, imagens, etc., a menos que explicitamente pedido.
    3. Retorne APENAS um JSON válido contendo uma lista de strings (caminhos dos arquivos).
    4. Exemplo de saída: {{"files": ["src/main.py", "src/utils/auth.py"]}}
    """

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        content = response.choices[0].message.content
        plan_json = json.loads(content)
        files_to_read = plan_json.get("files", [])
        
        state["reading_plan"] = files_to_read
        state["steps"].append(f"Planner: Selecionados {len(files_to_read)} arquivos para leitura.")
        logger.info(f"Arquivos selecionados pelo Planner: {files_to_read}")
        
    except Exception as e:
        error_msg = f"Erro no Planner: {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["reading_plan"] = []

    return state
