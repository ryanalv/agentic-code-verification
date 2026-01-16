# Agente responsável por revisar a documentação gerada, verificar alucinações e atribuir nota de qualidade.
from typing import Dict, List, Any, Optional
import os
import re
import json
from src.agents.react_core import ReActAgent
from src.utils.logger import logger

class CriticAgent:
    def __init__(self, model_name: str = "moonshotai/kimi-k2-thinking"):
        self.model_name = model_name
        self.agent = ReActAgent(model_name=model_name) # Usado para avaliação

    def check_hallucinations(self, text: str, project_path: str) -> List[str]:
        """
        Escaneia o texto por caminhos de arquivos e verifica se eles existem em project_path.
        Retorna uma lista de arquivos faltantes (alucinações).
        """
        # Regex para encontrar caminhos de arquivos: procura por palavras terminando em extensões ou dentro de backticks/links
        potential_files = set()
        
        # Encontra dentro de backticks `arquivo.ext`
        matches_ticks = re.findall(r'`([\w\/\\.-]+\.\w+)`', text)
        potential_files.update(matches_ticks)
        
        # Encontra links markdown [label](caminho)
        matches_links = re.findall(r'\]\(([\w\/\\.-]+\.\w+)\)', text)
        potential_files.update(matches_links)

        # Filtra falsos positivos comuns ou links externos
        filtered_files = [f for f in potential_files if not f.startswith('http')]
        
        missing_files = []
        for file_ref in filtered_files:
            # Normaliza separadores de caminho
            normalized_ref = file_ref.replace('/', os.sep).replace('\\', os.sep)
            
            # Remove barra inicial se presente para juntar corretamente
            if normalized_ref.startswith(os.sep):
                normalized_ref = normalized_ref[1:]
                
            full_path = os.path.join(project_path, normalized_ref)
            
            # Verificação simples: se arquivo não existe E não é um arquivo raiz comum que perdemos
            if not os.path.exists(full_path):
                # Tenta verificar se é relativo a src (comum em python)
                src_path = os.path.join(project_path, 'src', normalized_ref)
                if not os.path.exists(src_path):
                     missing_files.append(file_ref)
                     
        return missing_files

    def evaluate_quality(self, text: str) -> Dict[str, Any]:
        """
        Avalia a qualidade da documentação usando um LLM.
        Retorna um dicionário com 'score' (0-10) e 'feedback'.
        """
        prompt = f"""
        Você é um Crítico de Código e Documentação experiente.
        Avalie a qualidade da seguinte documentação técnica gerada automaticamente.
        
        Critérios de Avaliação (0-10):
        1. Clareza e Estrutura: A documentação está bem organizada e legível?
        2. Completude: Cobre arquitetura, fluxo de dados, dependências e configuração?
        3. Profundidade Técnica: Explica O QUE e COMO, não apenas lista arquivos?
        
        Documentação para análise:
        === INÍCIO ===
        {text[:8000]}  # Truncating to avoid context limits if necessary
        === FIM ===
        
        Retorne APENAS um JSON no seguinte formato (respeite a estrutura do Agente):
        {{
             "thought": "Analisei o texto e avaliei...",
             "final_answer": "{{\\"score\\": <nota>, \\"feedback\\": \\"<texto>\\", \\"reasoning\\": \\"<texto>\\"}}"
        }}
        
        Nota: O campo `final_answer` DEVE ser uma string contendo o JSON de avaliação escapado, ou apenas o JSON de avaliação.
        """
        
        # Usamos uma chamada direta ou um run simples já que queremos apenas processamento de texto.
        # Reusar ReActAgent.run funciona bem.
        try:
            result = self.agent.run(prompt)
            # ReActAgent retorna um dict agora, extrai final_answer
            final_answer = result.get("final_answer", "")
            usage = result.get("usage", {"total_tokens": 0})
            
            data = {}
            # Se final_answer já for um dict (LLM retornou objeto aninhado), usamos direto
            if isinstance(final_answer, dict):
                data = final_answer
            else:
                # Faz o parse do JSON da resposta
                try:
                    # Limpando blocos de código markdown se presente
                    clean_json = str(final_answer).replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_json)
                except json.JSONDecodeError:
                    logger.error(f"Falha ao processar JSON do Crítico: {final_answer}")
                    return {"score": 5, "feedback": "Erro ao analisar resposta do crítico. Formato inválido.", "reasoning": "Falha sistêmica.", "usage": usage}
            
            data["usage"] = usage
            return data
                
        except Exception as e:
            logger.error(f"Agente Crítico falhou: {e}")
            return {"score": 0, "feedback": f"Erro interno do crítico: {e}", "reasoning": "Exceção.", "usage": {"total_tokens": 0}}

    def review(self, analyst_output: str, project_path: str) -> Dict[str, Any]:
        """
        Orquestra o processo de revisão.
        """
        # 1. Verifica Alucinações
        hallucinations = self.check_hallucinations(analyst_output, project_path)
        
        # 2. Avalia Qualidade
        quality_assessment = self.evaluate_quality(analyst_output)
        
        score = quality_assessment.get("score", 0)
        feedback = quality_assessment.get("feedback", "")
        usage = quality_assessment.get("usage", {"total_tokens": 0})
        
        approved = True
        final_feedback = ""
        
        # Lógica de Aprovação
        if hallucinations:
            approved = False
            final_feedback += f"Problemas de Alucinação detectados: Os seguintes arquivos citados não existem no projeto: {', '.join(hallucinations)}. "
            score = max(0, score - 2) # Penaliza a nota
            
        if score < 7: # Limite
            approved = False
            final_feedback += f"Qualidade Insuficiente (Nota {score}/10): {feedback}"
        
        return {
            "approved": approved,
            "score": score,
            "feedback": final_feedback.strip(),
            "hallucinations": hallucinations,
            "quality_feedback": feedback,
            "usage": usage
        }
