import os
from openai import OpenAI
from src.core.state import AgentState
from src.utils.logger import logger

def writer_node(state: AgentState) -> AgentState:
    """
    Agente Writer: Sintetiza o contexto coletado em uma resposta final/documentação.
    """
    logger.info("--- Writer Node: Gerando resposta final ---")
    
    context = state.get("files_context", "")
    query = state.get("user_query", "")
    critique = state.get("critique_feedback", None)
    
    # Configuração do LLM
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    client = OpenAI(base_url="https://openrouter.ai/api/v1" if os.getenv("OPENROUTER_API_KEY") else None, api_key=api_key)
    model = "gpt-4o" # Modelo inteligente para escrita
    
    prompt = f"""
    Você é um Technical Writer Sênior.
    
    OBJETIVO: Escrever uma resposta técnica detalhada e precisa para a solicitação do usuário, baseada ESTRITAMENTE no contexto fornecido.
    
    SOLICITAÇÃO DO USUÁRIO: "{query}"
    
    CONTEXTO LIDO (CÓDIGO FONTE):
    {context[:100000]} # Limite de segurança de caracteres
    
    DIRETRIZES:
    1. Use Markdown profissional.
    2. Cite os arquivos analisados.
    3. Se o contexto for insuficiente, diga honestamente o que falta.
    4. Não invente classes ou funções que não estão no contexto.
    """
    
    if critique:
        prompt += f"""
        
        ATENÇÃO: Sua versão anterior foi criticada. Corrija os seguintes pontos:
        {critique}
        """

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content
        
        state["draft_response"] = content
        state["steps"].append("Writer: Resposta gerada.")
        
    except Exception as e:
        error_msg = f"Erro no Writer: {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["draft_response"] = f"Erro ao gerar resposta: {str(e)}"

    return state
