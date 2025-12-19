import os
import json
import re
from openai import OpenAI
from typing import List, Dict, Callable, Optional, Any
from src.config import settings
from src.utils.logger import logger

class ReActAgent:
    def __init__(self, model_name: str = "moonshotai/kimi-k2-thinking", tools: Dict[str, Callable] = None):
        api_key = settings.API_OPENROUTER_KEY
        if not api_key:
             raise ValueError("API_OPENROUTER_KEY environment variable not set")
        
        logger.debug(f"Loaded API Key: {api_key[:10]}...")
        
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.model_name = model_name
        self.tools = tools or {}
        self.max_steps = 15  # Increased steps for complex tasks
        
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
        """Attempts to parse the LLM response as JSON."""
        try:
            # Try direct parse
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON block ```json ... ```
            match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except:
                    pass
            
            # Try to find just { ... }
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except:
                    pass
            
            return None

    def run(self, goal: str, on_step_callback: Callable[[int, str], None] = None) -> str:
        system_prompt = self._build_system_prompt(goal)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Start."}
        ]
        
        logger.info(f"Starting ReAct Agent for goal: {goal[:50]}...")
        if on_step_callback:
            on_step_callback(0, "Iniciando análise...")
        
        for i in range(self.max_steps):
            # Generate next step
            if on_step_callback:
                on_step_callback(i+1, "Pensando...")
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    response_format={"type": "json_object"} # Force JSON mode if supported
                )
                output = response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"Error calling LLM: {e}")
                return f"Erro ao chamar LLM: {e}"
            
            logger.debug(f"Step {i+1} Output: {output}")
            
            # Append to history
            messages.append({"role": "assistant", "content": output})
            
            # Parse JSON
            parsed_output = self._parse_json_response(output)
            
            if not parsed_output:
                logger.warning(f"Step {i+1}: Invalid JSON received.")
                messages.append({"role": "user", "content": "Error: Invalid JSON format. Please output ONLY valid JSON matching the schema."})
                continue

            thought = parsed_output.get("thought", "")
            final_answer = parsed_output.get("final_answer")
            action = parsed_output.get("action")
            action_input = parsed_output.get("action_input")
            
            if on_step_callback and thought:
                # Show thought in progress (truncated)
                on_step_callback(i+1, f"Pensamento: {thought[:100]}...")

            # Check for Final Answer
            if final_answer:
                logger.info("Agent reached final answer.")
                return final_answer
            
            # Execute Action
            if action:
                if action in self.tools:
                    if on_step_callback:
                        on_step_callback(i+1, f"Executando {action}...")
                    
                    logger.info(f"Executing tool: {action} with input: {action_input}")
                    try:
                        observation = self.tools[action](action_input)
                    except Exception as e:
                        logger.error(f"Tool execution error: {e}")
                        observation = f"Error executing tool: {e}"
                else:
                    observation = f"Error: Tool '{action}' not found."
                
                logger.debug(f"Observation: {str(observation)[:200]}...")
                
                # Feed observation back
                observation_json = json.dumps({"observation": observation})
                messages.append({"role": "user", "content": observation_json})
            else:
                # No action and no final answer?
                messages.append({"role": "user", "content": "Error: You must provide either an 'action' or a 'final_answer'."})

        return "Agente excedeu o tempo limite ou falhou em chegar a uma conclusão."
