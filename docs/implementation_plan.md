# Plano de Implementação - Agente Crítico de Qualidade de Código
**Objetivo:** Desenvolver um sistema onde um Agente Crítico avalia e melhora o output de um Code Analyst, com métricas definidas e documentadas.
**Prazo:** 3 Dias.

## Estrutura do Projeto (Sugestão)
```
/ai-quality-critic-agent
  /src
    /agents
      critic_agent.py      # O Agente que avalia
      analyst_agent.py     # O Agente que gera o código (Mock ou Real)
    /core
      llm.py              # Configurações de LLM
      prompts.py          # Prompts do Crítico e Analista
    /utils
      logger.py           # Logging estruturado
  /notebooks
    metrics_analysis.ipynb # Notebook para análise de qualidade e custos
  /docs
    project_choices.md    # O "Doc Word" com as escolhas
  run_pipeline.py         # Script principal de execução
```

## Cronograma de 3 Dias

### Dia 1: A Base e o Agente Crítico (Engenharia de Software)
**Foco:** Construir o loop de interação.
1.  **Setup do Ambiente:**
    -   Garantir dependências (`langchain`, `openai`, `pandas`, `pytest`).
    -   Configurar `.env`.
2.  **Mock do `CodeAnalyst`:**
    -   Criar uma função/agente que gera código (pode ser propositalmente ruim no início para testar o crítico).
    -   *Input:* "Crie uma função fibonacci". *Output:* Código Python.
3.  **Desenvolvimento do `CriticAgent`:**
    -   **Persona:** Tech Lead / QA Engineer.
    -   **Prompt:** Instruções para identificar bugs, segurança, estilo (PEP8) e completude.
    -   **Tools:**
        -   `verify_syntax(code_string)`: Roda `ast.parse()` para checar sintaxe válida.
        -   `run_tests(code_string, test_cases)`: Roda o código contra casos de teste com `exec` (sandbox cuidado) ou subprocess.
    -   **Feedback Loop:** Se o Crítico rejeitar, devolve o feedback para o Analista regenerar. Defina o `MAX_ITERATIONS` (ex: 3) para evitar loops infinitos.

### Dia 2: Métricas e Validação (Ciência de Dados)
**Foco:** Medir o que está acontecendo.
1.  **Notebook de Métricas (`metrics_analysis.ipynb`):**
    -   **Coleta de Dados:** Salvar cada interação (Input User, Output Analyst, Avaliação Critic, Output Final) em um JSON/CSV.
2.  **Implementar Métricas:**
    -   **Custo:** Contar tokens (input/output) por execução.
    -   **Qualidade Técnica:** O código final roda? Passa nos testes unitários?
    -   **Eficiência do Crítico:** Taxa de aprovação na 1ª tentativa vs. precisão da crítica.
    -   **Alucinação (Proxy):** Usar o `CriticAgent` para verificar se o código usa bibliotecas que não existem (import check).
3.  **Teste de Stress:**
    -   Forçar o Analista a gerar código com erros comuns (syntax error, infinite loop) e ver se o Crítico pega.

### Dia 3: Refinamento, Documentação e Entrega
**Foco:** Consolidar e Documentar.
1.  **Ajuste Fino:**
    -   Melhorar o prompt do Crítico com base nos erros do Dia 2.
2.  **Documentação (`project_choices.md`):**
    -   Escrever o "Doc" explicando por que escolheu LangChain/Autogen/Raw OpenAI.
    -   Justificar as métricas escolhidas.
3.  **Empacotamento:**
    -   Limpar o repo.
    -   Atualizar `README.md` com instruções de como rodar.

## User Review Required
> [!IMPORTANT]
> A execução de código gerado por IA (`run_tests`) deve ser feita com cautela. Para o MVP de 3 dias, `exec` local pode ser aceitável se supervisionado, mas o ideal seria Docker.
