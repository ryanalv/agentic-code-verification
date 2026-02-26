# cli.py - Interface de Linha de Comando (Terminal) pura para o Agente Crítico
import argparse
import os
import sys
import datetime
import json
import asyncio
import contextvars
from dotenv import load_dotenv

load_dotenv()

# Garante que o diretório raiz esteja no PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.code_analyst import analyze_codebase
from src.utils.logger import logger

def main():
    parser = argparse.ArgumentParser(description="AI Quality Critic Agent (CLI Mode)")
    parser.add_argument("project_path", type=str, nargs="?", default=".", help="Caminho do projeto para ser analisado (padrão: diretório atual)")
    parser.add_argument("--domain", "-d", type=str, default=None, help="Caminho opcional para a pasta de RAG/Conhecimento de Domínio")
    
    args = parser.parse_args()
    
    # Tratamento de caminhos
    project_path = os.path.abspath(args.project_path)
    domain_path = os.path.abspath(args.domain) if args.domain else None
    project_name = os.path.basename(project_path) if os.path.basename(project_path) else "Target_Project"
    
    if not os.path.exists(project_path):
        print(f"\n[ERRO] O caminho do projeto não existe: {project_path}")
        sys.exit(1)

    print("="*60)
    print(f"🚀 INICIANDO ANÁLISE AGÊNTICA (MODO TERMINAL) 🚀")
    print("="*60)
    print(f"📁 Projeto Alvo: {project_path}")
    if domain_path:
        print(f"🧠 RAG Domínio : {domain_path}")
    print(f"⏳ Isso pode levar alguns minutos devido à profundidade da análise...")
    print("="*60)

    logger.info(f"CLI Iniciada. Projeto: {project_path} | Dominio: {domain_path}")

    try:
        # A chamada de análise já incorpora o AgentWorkflow com loop de max_iterations=3 e CriticAgent interno.
        # Assim evitamos o double-looping que acontecia entre o AgentWorkflow e a interface Web.
        result = analyze_codebase(
            project_path=project_path,
            project_name=project_name,
            feedback=None,
            domain_knowledge_path=domain_path
        )
        
        # O retorno é um dicionário contendo "final_answer", "steps", e "details"
        final_answer = result.get("final_answer", "")
        
        # Assegura que a saída seja uma string
        if isinstance(final_answer, (dict, list)):
            doc_text = json.dumps(final_answer, ensure_ascii=False, indent=2)
        else:
            doc_text = str(final_answer)

        steps = result.get("steps", 0)
        
        # ---- Salvamento Local do Documento ----
        docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_docs")
        os.makedirs(docs_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_project_name = "".join([c for c in project_name if c.isalnum() or c in (' ', '-', '_')]).strip().replace(" ", "_")
        filename = f"{safe_project_name}_{timestamp}.md"
        file_path = os.path.join(docs_dir, filename)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(doc_text)
            
        print("\n" + "="*60)
        print("✅ ANÁLISE CONCLUÍDA COM SUCESSO!")
        print(f"📊 Passos Executados: {steps}")
        print(f"💾 Documentação Salva em:\n   -> {file_path}")
        print("="*60 + "\n")
        logger.info(f"CLI Finalizada com Sucesso. Salvo em: {file_path}")

    except KeyboardInterrupt:
        print("\n\n[AVISO] Análise interrompida pelo usuário.")
        logger.warning("CLI Interrompida pelo usuário.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n[ERRO CRÍTICO] A análise falhou: {e}")
        logger.error(f"Falha na CLI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
