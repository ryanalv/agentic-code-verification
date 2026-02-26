import os
import concurrent.futures
from openai import OpenAI
from src.core.state import AgentState
from src.utils.logger import logger

def _analyze_chunk(chunk: str, query: str, critique: str, client: OpenAI, model: str) -> str:
    """
    Sub-agente que analisa uma parte do contexto detalhadamente.
    """
    prompt = f"""
    Você é um Agente Analista Setorial Sênior.
    OBJETIVO: Escrever uma análise técnica PROFUNDA, exaustiva e formal ESTRITAMENTE sobre o trecho de código fornecido abaixo.
    
    SOLICITAÇÃO PRINCIPAL DO USUÁRIO: "{query}"

    REGRAS DE OURO PARA ESTA ANÁLISE:
    1. Jamais abrevie ou pule componentes - detalhe clara e formalmente cada classe, função e fluxo do trecho. Você está escrevendo a documentação oficial para um time externo que NÃO terá acesso ao código fonte. Se faltar detalhe, o sistema será implementado incorretamente. Seja exaustivo.
    2. A documentação deve ser descritiva e direta ao ponto. Explique o "porquê" e o "como" das coisas de forma didática e muito clara.
    3. Mantenha um tom profissional, mas acessível. O texto será lido por estagiários e seniores.
    4. Você DEVE incluir em sua análise:
       - Explicação conceitual
       - Fluxo de execução passo a passo
       - Pseudocódigo
       - Casos de erro
       - Decisões arquiteturais
       - Tradeoffs
       - Exemplos práticos
       - Integração com outras partes do sistema
    5. Estrutura primeiro. Texto depois. Antes de escrever o texto final detalhado, você DEVE gerar um bloco JSON válido contendo exatamente as seguintes chaves (preencha as listas correspondentes com os pontos identificados):
    {{
      "decisoes_arquiteturais": [],
      "riscos": [],
      "limitações": [],
      "tradeoffs": [],
      "fluxo_detalhado": [],
      "contratos_publicos": []
    }}
    Depois de gerar a estrutura JSON, transforme todas essas informações em um texto narrativo EXAUSTIVO e PROFUNDO.
    
    TRECHO DE CÓDIGO A ANALISAR:
    {chunk[:100000]} # Limite de segurança
    """
    
    if critique:
        prompt += f"\n\nCRÍTICAS ANTERIORES A SEREM CORRIGIDAS:\n{critique}"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Erro no Analista Setorial: {e}")
        return f"[ERRO NA ANÁLISE DO TRECHO]: {str(e)}"

def writer_node(state: AgentState) -> AgentState:
    """
    Agente Writer: Utiliza abordagem Map-Reduce. 
    1. Quebra o contexto em blocos.
    2. Usa múltiplos Agentes Analistas Setoriais em paralelo.
    3. Usa um Agente Editor Mestre para compilar a documentação final.
    """
    logger.info("--- Writer Node: Iniciando Fase Map-Reduce (Múltiplos Agentes) ---")
    
    context = state.get("files_context", "")
    rag_context = state.get("rag_context", "")
    query = state.get("user_query", "")
    critique = state.get("critique_feedback", None)
    
    has_valid_files = context and "Nenhum arquivo" not in context
    has_valid_rag = rag_context and "Erro no RAG" not in rag_context and "Nenhum contexto" not in rag_context
    
    if not has_valid_files and not has_valid_rag:
         state["draft_response"] = "Não há arquivos suficientes ou contexto RAG para gerar documentação."
         return state

    # Configuração do LLM
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
    worker_model = deployment_name
    master_model = deployment_name

    # 1. PARTICIONAMENTO (MAP PREP)
    # Dividindo o texto por marcador de classe/arquivo ou em chunks arbitrários caso muito longo.
    chunks = []
    # Usando o padrão definido em reader_node para particionar
    raw_chunks = context.split("=== CLASSE/ARQUIVO:")
    for rc in raw_chunks:
        if rc.strip():
            chunks.append("=== CLASSE/ARQUIVO:" + rc)
            
    logger.info(f"Writer: Contexto particionado em {len(chunks)} trechos para sub-agentes.")
    
    # 2. FASE MAP (SUB-AGENTES PARALELOS)
    analyzed_sections = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(_analyze_chunk, chunk, query, critique, client, worker_model) 
            for chunk in chunks
        ]
        for future in concurrent.futures.as_completed(futures):
            analyzed_sections.append(future.result())
            logger.info("Writer: Sub-agente concluiu uma análise.")
            
    compiled_sections = "\n\n".join(analyzed_sections)

    # 3. FASE REDUCE (AGENTE EDITOR MESTRE)
    logger.info("Writer: Iniciando Agente Editor Mestre para compilação final.")
    
    master_prompt = f"""
    Você é o Agente Editor Mestre (Arquiteto Sênior).
    OBJETIVO: Receber diversas análises setoriais de partes do código e unificá-las em uma GIGANTESCA e ÚNICA Documentação Técnica.
    
    SOLICITAÇÃO ORIGINAL: "{query}"
    
    REGRAS DE OURO:
    1. A documentação final deve ser extremamente EXAUSTIVA e DETALHADA. Você está escrevendo a documentação oficial para um time externo que NÃO terá acesso ao código fonte. Se faltar detalhe, o sistema será implementado incorretamente. Seja exaustivo.
    2. PÚBLICO-ALVO MISTO: O documento será lido por Desenvolvedores Seniores, Juniores, Estagiários e pessoas não-técnicas. Use explicações didáticas, analogias acessíveis e linguagem clara para explicar arquiteturas complexas antes de aprofundar nos detalhes puramente técnicos.
    3. SEMPRE crie uma seção de "Contexto Teórico da Arquitetura". Identifique quais tecnologias ou padrões o projeto usa (por exemplo, RAG, Bancos Vetoriais, Agentes, Hexagonal, MVC) e use a sua BASE DE CONHECIMENTO INTERNA para explicar teoricamente esses conceitos e DEPOIS como eles se aplicam especificamente ao código lido.
    4. DIAGRAMAS EXIGIDOS: É **OBRIGATÓRIO** incluir diagramas visuais na sua documentação. Para isso, use EXCLUSIVAMENTE arte ASCII formatada em TABELAS.
    5. Você DEVE consolidar TODA a riqueza de detalhes contida nas análises setoriais. Nas seções detalhadas, garanta que os seguintes pontos estejam SEMPRE presentes: Explicação conceitual, Fluxo de execução passo a passo, Pseudocódigo, Casos de erro, Decisões arquiteturais, Tradeoffs, Exemplos práticos, Integração com outras partes do sistema.
    6. Formate tudo em Markdown profissional. As análises setoriais receberam ordens de criar arrays JSON (riscos, limitações, etc.); incorpore o conteúdo desses JSONs no texto final de forma fluida, legível e exaustiva. Não oculte nenhuma informação valiosa.

    
    === CONTEXTO ADICIONAL / CONHECIMENTO DE DOMÍNIO (VIA RAG) ===
    {rag_context[:30000]}
    (Utilize este contexto para embasar a análise do domínio, arquitetura e regras de negócio)

    === ANÁLISES SETORIAIS COLETADAS DOS CÓDIGOS ===
    {compiled_sections[:200000]}
    """
    
    if critique:
        master_prompt += f"\n\nATENÇÃO - CRÍTICA DA TENTATIVA ANTERIOR:\n{critique}\n\nVocê falhou na iteração anterior. Corrija os ponteiros levantados e gere uma documentação mais madura.\n"
        
    try:
        response = client.chat.completions.create(
            model=master_model,
            messages=[{"role": "user", "content": master_prompt}],
            temperature=0.5,
        )
        content = response.choices[0].message.content
        
        state["draft_response"] = content
        state["steps"].append(f"Writer: Documentação montada combinando {len(chunks)} análises.")
        logger.info("Writer Node: Draft finalizado com sucesso.")
        
    except Exception as e:
        error_msg = f"Erro no Agente Mestre (Writer): {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["draft_response"] = f"Erro ao compilar documentação: {str(e)}"

    return state
