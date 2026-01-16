# Servidor FastAPI que provê a interface web e gerencia o fluxo de análise em tempo real (SSE).
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import json
import os
import sys
import contextvars

# Garante que a raiz do projeto está no path para que 'import src.xxx' funcione
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.code_analyst import analyze_codebase
from src.agents.critic import CriticAgent
from src.config import settings
from src.utils.logger import logger, set_step, set_tokens, add_tokens, current_step, current_tokens
import datetime

app = FastAPI()

# Monta arquivos estáticos
# Monta arquivos estáticos com caminho absoluto
STATIC_DIR = os.path.join(PROJECT_ROOT, "src", "web", "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modo Mock / Real
USE_MOCK = os.getenv("OPENROUTER_API_KEY") is None

async def run_analysis_generator(project_path_arg):
    """
    Generator that runs the analysis loop and yields SSE events.
    """
    # Se não for passado caminho, usa o src do próprio projeto
    if not project_path_arg or project_path_arg.strip() == "":
        project_path = os.path.join(PROJECT_ROOT, "src")
        project_name = "AI Quality Critic Agent (Self-Analysis)"
    else:
        project_path = project_path_arg.strip()
        project_name = os.path.basename(project_path) if os.path.basename(project_path) else "Target Project"
    
    # Initialize Context
    set_step("Initialization")
    set_tokens(0)
    
    start_msg = f"Iniciando análise em: {project_path}"
    logger.info(start_msg)
    yield f"data: {json.dumps({'type': 'log', 'timestamp': datetime.datetime.now().strftime('%H:%M:%S'), 'step': current_step.get(), 'tokens': current_tokens.get(), 'message': start_msg})}\n\n"
    
    critic = None
    if not USE_MOCK:
        try:
            critic = CriticAgent()
            msg = "Agente Crítico inicializado."
            logger.info(msg)
            yield f"data: {json.dumps({'type': 'log', 'timestamp': datetime.datetime.now().strftime('%H:%M:%S'), 'step': current_step.get(), 'tokens': current_tokens.get(), 'message': msg})}\n\n"
        except Exception as e:
            err_msg = f"Erro ao inicializar Crítico: {e}"
            logger.error(err_msg)
            yield f"data: {json.dumps({'type': 'error', 'timestamp': datetime.datetime.now().strftime('%H:%M:%S'), 'step': current_step.get(), 'tokens': current_tokens.get(), 'message': err_msg})}\n\n"
            yield f"data: {json.dumps({'type': 'warning', 'message': 'Continuando em modo Mock devido a erro na API.'})}\n\n"
    
    current_feedback = None
    max_retries = 2
    
    for i in range(max_retries + 1):
        step_name = f"Round {i+1} - Analyst"
        set_step(step_name)
        yield f"data: {json.dumps({'type': 'status', 'message': f'Iteração {i+1}: Executando Analista de Código...'})}\n\n"
        
        msg = "Analista está lendo arquivos e gerando documentação..."
        logger.info(msg)
        yield f"data: {json.dumps({'type': 'log', 'timestamp': datetime.datetime.now().strftime('%H:%M:%S'), 'step': step_name, 'tokens': current_tokens.get(), 'message': msg})}\n\n"
        
        # 1. Executar Analista
        analyst_start = asyncio.get_event_loop().time()
        
        if USE_MOCK:
             # Atraso mock
            await asyncio.sleep(2)
            if i == 0:
                doc_text = "Documentação v1 (com erro)\nReferência: `src/ghost_file.py`\nQualidade baixa."
                steps = 5
            else:
                doc_text = "Documentação v2 (Corrigida)\nReferência: `src/code_analyst.py`\nQualidade alta."
                steps = 6
            usage = {"total_tokens": 500}
        else:
             # Execução real
             # Nota: Isto é bloqueante, em uma aplicação real deveria estar em um threadpool
             loop = asyncio.get_event_loop()
             try:
                # Verificando se o caminho existe
                if not os.path.exists(project_path):
                     raise FileNotFoundError(f"Caminho não encontrado: {project_path}")

                # Captura contexto para propagar para a thread
                ctx = contextvars.copy_context()
                analyze_func = lambda: analyze_codebase(project_path, project_name, current_feedback)
                result = await loop.run_in_executor(None, ctx.run, analyze_func)
                doc_text = result.get("final_answer", "")
                steps = result.get("steps", 0)
                usage = result.get("usage", {})
             except Exception as e:
                 yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                 break

        tokens_used = usage.get("total_tokens", 0)
        if isinstance(tokens_used, int):
            add_tokens(tokens_used)
        
        msg = f"Analista finalizou em {steps} passos. Tokens estimados bloco: {tokens_used}"
        logger.info(msg)
        yield f"data: {json.dumps({'type': 'log', 'timestamp': datetime.datetime.now().strftime('%H:%M:%S'), 'step': current_step.get(), 'tokens': current_tokens.get(), 'message': msg})}\n\n"
        yield f"data: {json.dumps({'type': 'doc_preview', 'content': doc_text[:500] + '...'})}\n\n"
        
        # 2. Executar Crítico
        step_name = f"Round {i+1} - Critic"
        set_step(step_name)
        yield f"data: {json.dumps({'type': 'status', 'message': f'Iteração {i+1}: Executando Agente Crítico...'})}\n\n"
        
        if USE_MOCK or critic is None:
            await asyncio.sleep(1)
            if i == 0:
                 review = {"approved": False, "score": 5, "feedback": "Arquivo inexistente citado.", "hallucinations": ["src/ghost_file.py"]}
            else:
                 review = {"approved": True, "score": 9, "feedback": "Excelente.", "hallucinations": []}
        else:
            loop = asyncio.get_event_loop()
            ctx = contextvars.copy_context()
            review_func = lambda: critic.review(doc_text, project_path)
            review = await loop.run_in_executor(None, ctx.run, review_func)
            
        # Rastreia tokens do Crítico
        critic_usage = review.get("usage", {})
        critic_tokens = critic_usage.get("total_tokens", 0)
        if isinstance(critic_tokens, int):
            add_tokens(critic_tokens)

        # Loga fim do crítico
        msg = f"Crítico finalizou. Tokens estimados bloco: {critic_tokens}"
        logger.info(msg)
        yield f"data: {json.dumps({'type': 'log', 'timestamp': datetime.datetime.now().strftime('%H:%M:%S'), 'step': current_step.get(), 'tokens': current_tokens.get(), 'message': msg})}\n\n"
            
        yield f"data: {json.dumps({'type': 'metrics', 'score': review['score'], 'hallucinations': len(review['hallucinations']), 'approved': review['approved'], 'total_tokens': current_tokens.get()})}\n\n"
        
        if review['approved']:
            yield f"data: {json.dumps({'type': 'success', 'message': 'Documentação APROVADA pelo Crítico!'})}\n\n"
            yield f"data: {json.dumps({'type': 'final_doc', 'content': doc_text})}\n\n"
            break
        else:
            current_feedback = review['feedback']
            yield f"data: {json.dumps({'type': 'warning', 'message': f'Reprovado. Feedback: {current_feedback}'})}\n\n"
            if i == max_retries:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Limite de tentativas excedido.'})}\n\n"

    yield "data: [DONE]\n\n"

@app.get("/")
async def get_index():
    template_path = os.path.join(PROJECT_ROOT, "src", "web", "templates", "index.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/stream_analysis")
async def stream_analysis(project_path: str = ""):
    return StreamingResponse(run_analysis_generator(project_path), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run("src.server:app", host="127.0.0.1", port=8000, reload=True)
