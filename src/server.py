from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import json
import os
import sys

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.code_analyst import analyze_codebase
from src.agents.critic import CriticAgent
from src.config import settings

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock / Real mode
USE_MOCK = os.getenv("OPENROUTER_API_KEY") is None

async def run_analysis_generator():
    """
    Generator that runs the analysis loop and yields SSE events.
    """
    project_path = os.path.join(os.getcwd(), "src") # Analyze itself
    project_name = "AI Quality Critic Agent"
    
    yield f"data: {json.dumps({'type': 'log', 'message': f'Iniciando análise em: {project_path}'})}\n\n"
    
    critic = CriticAgent()
    current_feedback = None
    max_retries = 2
    
    for i in range(max_retries + 1):
        yield f"data: {json.dumps({'type': 'status', 'message': f'Iteração {i+1}: Executando Analista de Código...'})}\n\n"
        yield f"data: {json.dumps({'type': 'log', 'message': 'Analista está lendo arquivos e gerando documentação...'})}\n\n"
        
        # 1. Run Analyst
        analyst_start = asyncio.get_event_loop().time()
        
        if USE_MOCK:
             # Mock delay
            await asyncio.sleep(2)
            if i == 0:
                doc_text = "Documentação v1 (com erro)\nReferência: `src/ghost_file.py`\nQualidade baixa."
                steps = 5
            else:
                doc_text = "Documentação v2 (Corrigida)\nReferência: `src/code_analyst.py`\nQualidade alta."
                steps = 6
            usage = {"total_tokens": 500}
        else:
             # Real execution
             # Note: This is blocking, in a real app should be in a threadpool
             loop = asyncio.get_event_loop()
             try:
                result = await loop.run_in_executor(None, analyze_codebase, project_path, project_name, current_feedback)
                doc_text = result.get("final_answer", "")
                steps = result.get("steps", 0)
                usage = result.get("usage", {})
             except Exception as e:
                 yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                 break

        tokens = usage.get("total_tokens", "?")
        yield f"data: {json.dumps({'type': 'log', 'message': f'Analista finalizou em {steps} passos. Tokens estimados: {tokens}'})}\n\n"
        yield f"data: {json.dumps({'type': 'doc_preview', 'content': doc_text[:500] + '...'})}\n\n"
        
        # 2. Run Critic
        yield f"data: {json.dumps({'type': 'status', 'message': f'Iteração {i+1}: Executando Agente Crítico...'})}\n\n"
        
        if USE_MOCK:
            await asyncio.sleep(1)
            if i == 0:
                 review = {"approved": False, "score": 5, "feedback": "Arquivo inexistente citado.", "hallucinations": ["src/ghost_file.py"]}
            else:
                 review = {"approved": True, "score": 9, "feedback": "Excelente.", "hallucinations": []}
        else:
            loop = asyncio.get_event_loop()
            review = await loop.run_in_executor(None, critic.review, doc_text, project_path)
            
        yield f"data: {json.dumps({'type': 'metrics', 'score': review['score'], 'hallucinations': len(review['hallucinations']), 'approved': review['approved']})}\n\n"
        
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
    with open("src/web/templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/stream_analysis")
async def stream_analysis():
    return StreamingResponse(run_analysis_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run("src.server:app", host="0.0.0.0", port=8000, reload=True)
