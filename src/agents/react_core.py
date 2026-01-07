import os
import json
import re
from openai import OpenAI
from typing import List, Dict, Callable, Optional, Any
from src.config import settings
from src.utils.logger import logger

class ReActAgent:
    def __init__(self, model_name: str = "moonshotai/kimi-k2-thinking", tools: Dict[str, Callable] = None):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
             # Se não houver chave, deixamos falhar apenas ao tentar chamar o LLM, 
             # ou permitimos se o objetivo for simulação.
             # Para correção imediata do crash na inicialização:
             pass 
        
        logger.debug(f"Loaded API Key: {api_key[:10]}...")
        
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.model_name = model_name
        self.tools = tools or {}
        self.max_steps = 15  # Aumentados os passos para tarefas complexas
        
    def _build_system_prompt(self, goal: str) -> str:
        tool_descriptions = "\n".join([f"- {name}: {func.__doc__}" for name, func in self.tools.items()])
        
        return f"""
Você é um agente de pesquisa inteligente. Seu objetivo é: {goal}

Você tem acesso às seguintes ferramentas:
{tool_descriptions}

Você deve fornecer sua resposta no formato ESTRITO JSON. Não forneça nada além do bloco JSON.
O JSON deve seguir um destes dois esquemas:

Esquema 1 (Para usar uma ferramenta):
{{
    "thought": "Seu raciocínio sobre o que fazer a seguir (em Português)",
    "action": "nome_da_ferramenta",
    "action_input": "string_de_argumento"
}}

Esquema 2 (Quando você terminar):
{{
    "thought": "Seu raciocínio do porquê você terminou",
    "final_answer": "O resultado final ou documentação solicitada (em Português)"
}}

Regras:
1. Você DEVE usar as ferramentas para coletar informações. Não alucine fatos.
2. Se precisar pesquisar, use 'web_search'.
3. Se precisar ler uma página, use 'scrape_page'.
4. O 'action_input' deve ser uma string. Se a ferramenta espera um objeto complexo, serialize-o ou passe o caminho da string.
5. Produza APENAS o JSON.
"""

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Tenta analisar a resposta do LLM como JSON."""
        try:
            # Tenta análise direta
            return json.loads(response)
        except json.JSONDecodeError:
            # Tenta encontrar bloco JSON ```json ... ```
            match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except:
                    pass
            
            # Tenta encontrar apenas { ... }
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except:
                    pass
            
            return None

    def run(self, goal: str, on_step_callback: Callable[[int, str], None] = None) -> Dict[str, Any]:
        system_prompt = self._build_system_prompt(goal)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Start."}
        ]
        
        logger.info(f"Iniciando Agente ReAct para objetivo: {goal[:50]}...")
        if on_step_callback:
            on_step_callback(0, "Iniciando análise...")
        
        for i in range(self.max_steps):
            # Gera próximo passo
            if on_step_callback:
                on_step_callback(i+1, "Pensando...")
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    response_format={"type": "json_object"} # Força modo JSON se suportado
                )
                output = response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"Erro ao chamar LLM: {e}")
                return {
                    "final_answer": f"Erro ao chamar LLM: {e}",
                    "steps": i,
                    "usage": {"total_tokens": 0}
                }
            
            logger.debug(f"Passo {i+1} Saída: {output}")
            
            # Anexa ao histórico
            messages.append({"role": "assistant", "content": output})
            
            # Parse JSON
            parsed_output = self._parse_json_response(output)
            
            if not parsed_output:
                logger.warning(f"Passo {i+1}: JSON inválido recebido.")
                messages.append({"role": "user", "content": "Error: Invalid JSON format. Please output ONLY valid JSON matching the schema."})
                continue

            thought = parsed_output.get("thought", "")
            final_answer = parsed_output.get("final_answer")
            action = parsed_output.get("action")
            action_input = parsed_output.get("action_input")
            
            if on_step_callback and thought:
                # Mostra o pensamento em progresso (truncado)
                on_step_callback(i+1, f"Pensamento: {thought[:100]}...")

            # Verifica Resposta Final
            if final_answer:
                logger.info("Agente alcançou a resposta final.")
                usage_obj = getattr(response, 'usage', None)
                usage_dict = {"total_tokens": 0}
                if usage_obj:
                    # Verifica se é um objeto pydantic ou dict
                    if hasattr(usage_obj, "model_dump"):
                        usage_dict = usage_obj.model_dump()
                    elif hasattr(usage_obj, "dict"):
                        usage_dict = usage_obj.dict()
                    elif isinstance(usage_obj, dict):
                         usage_dict = usage_obj
                    elif hasattr(usage_obj, "total_tokens"):
                        usage_dict = {"total_tokens": usage_obj.total_tokens}
                
                return {
                    "final_answer": final_answer,
                    "steps": i + 1,
                    "usage": usage_dict
                }
            
            # Executa Ação
            if action:
                if action in self.tools:
                    if on_step_callback:
                        on_step_callback(i+1, f"Executando {action}...")
                    
                    logger.info(f"Executando ferramenta: {action} com entrada: {action_input}")
                    try:
                        observation = self.tools[action](action_input)
                    except Exception as e:
                        logger.error(f"Erro na execução da ferramenta: {e}")
                        observation = f"Erro executando ferramenta: {e}"
                else:
                    observation = f"Erro: Ferramenta '{action}' não encontrada."
                
                logger.debug(f"Observação: {str(observation)[:200]}...")
                
                # Devolve observação
                observation_json = json.dumps({"observation": observation})
                messages.append({"role": "user", "content": observation_json})
            else:
                # Sem ação e sem resposta final?
                messages.append({"role": "user", "content": "Erro: Você deve fornecer 'action' ou 'final_answer'."})

        return {
            "final_answer": "Agente excedeu o tempo limite ou falhou em chegar a uma conclusão.",
            "steps": self.max_steps,
            "usage": {"total_tokens": 0} # Placeholder/Estimativa
        }
