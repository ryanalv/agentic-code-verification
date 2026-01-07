# Guia do Projeto: Agente Crítico de Qualidade (AI Critic Agent)

Este documento serve como seu guia mestre para executar o projeto nos próximos 3 dias. Ele cobre as decisões arquiteturais, métricas e o racional por trás de cada escolha, conforme solicitado.

## Explorando os Componentes Existentes
O projeto já possui uma base estrutural importante que deve ser utilizada:

### `src/agents/react_core.py`
Este é o **motor do agente**. Ele implementa a lógica "ReAct" (Reason + Act), permitindo que o agente pense antes de agir.
-   **Classe `ReActAgent`**: Gerencia o loop de pensamento.
-   **Prompt do Sistema**: Define estritamente que o agente deve responder em JSON com `thought`, `action`, e `action_input`.
-   **Execução de Tools**: Ele recebe um dicionário de funções (`tools`) e sabe como chamá-las quando o modelo solicita.
-   **Tratamento de Erros**: Tenta corrigir JSONs inválidos e captura exceções das ferramentas.
**Por que é importante?** Você não precisa reinventar a roda. Seus agentes (`CriticAgent` e `AnalystAgent`) devem instanciar ou herdar desta classe para ganhar "poderes" de uso de ferramentas imediatamente.

### `src/config`
Centraliza as configurações do sistema para evitar "números mágicos" e chaves hardcoded.
-   Provavelmente contém um arquivo como `settings.py` que carrega variáveis de ambiente do `.env` (chaves de API, modelos padrão, timeouts).
-   **Como usar**: Importe `settings` de lá em vez de usar `os.getenv` espalhado pelo código.

### `src/utils`
Ferramentas utilitárias compartilhadas.
-   **Logger**: Configuração centralizada de logs para garantir que tudo seja gravado tanto no console quanto em arquivos de forma padronizada.
-   Outros helpers para manipulação de string ou JSON podem estar aqui.

### `data/`
Diretório destinado a armazenamento de arquivos persistentes gerados ou consumidos pela aplicação, que não são código fonte.
-   **Logs**: O arquivo `app.log` reside aqui, contendo o histórico de execução (útil para auditoria e debugging).
-   **DBs Locais**: Se usarmos SQLite ou CSVs de métricas, eles devem ser salvos aqui.

## 1. O Conceito (O que estamos construindo?)
Estamos criando um sistema de **Self-Refining (Auto-Refinamento)**.
Em vez de pedir código uma vez e aceitar (Zero-Shot), criamos um laço onde:
1.  **Analyst** gera o rascunho.
2.  **Critic** avalia o rascunho com critérios rigorosos.
3.  Se falhar, **Critic** dá feedback detalhado e pedimos ao **Analyst** para corrigir.
4.  Repetimos até passar ou atingir limite de tentativas.

### Arquitetura Visual
```mermaid
graph TD
    User[User Input] --> Analyst
    Analyst[Code Analyst Agent] -->|Gera Código| Critic
    Critic[Critic Agent] -->|Avalia| Decision{Aprovado?}
    Decision -- Não -->|Feedback + Erros| Analyst
    Decision -- Sim --> Final[Output Final Validado]
    Decision -- Max Retries --> Log[Log de Falha]
```

## 2. Decisões de Engenharia (O "Porquê")

### Por que um Agente separado para Crítica?
-   **Separação de Preocupações (Separation of Concerns):** O modelo que gera código muitas vezes "cega" para seus próprios erros. Mudar a persona para "QA" ou "Reviewer" quebra viés de confirmação.
-   **Prompt Especializado:** O prompt do crítico foca apenas em *achar defeito*, enquanto o do analista foca em *resolver o problema*.

### Quais Tools o Crítico deve usar?
Um crítico humano não apenas "olha"; ele roda, ele testa. O agente deve ter ferramentas análogas:
1.  **`syntax_checker`**: (Essencial) Antes de ler logica, valide se o Python/JS é válido `ast.parse()`. É barato e rápido.
2.  **`linter`**: (Opcional) Ferramenta como `pylint` ou `flake8` para qualidade estática.
3.  **`execution_sandbox`**: (Avançado) Rodar o código. *Cuidado:* Para este projeto de 3 dias, usar `exec()` com timeouts e restrições de import pode bastar, mas em produção usaríamos Docker Containers.

### Logs e Observabilidade
Você precisa saber o que aconteceu "dentro da cabeça" do agente.
-   **Trace de Conversa:** Guarde cada mensagem: `[User -> Analyst -> Critic -> Analyst (v2)...]`.
-   **Motivo da Rejeição:** Por que o crítico rejeitou? Sintaxe? Lógica? Estilo?

## 3. Pensando como Cientista de Dados (Métricas)

O notebook de métricas deve responder: "Meu agente é bom?".

### A. Métricas de Qualidade (Taste/Quality)
-   **Taxa de Aprovação de Primeira (First Pass Yield):** Quantas vezes o Analyst acertou de primeira?
-   **Taxa de Correção (Fix Rate):** Quando o Critic rejeita, o Analyst consegue consertar na próxima? Ou ele entra em loop de erro?
-   **Pass Rate Final:** Ao final de N iterações, quantos % das tarefas resultaram em código executável?

### B. Métricas de Custo e Eficiência
-   **Tokens por Solução:** Quanto custa (Input/Output tokens) para resolver um problema simples vs complexo. O loop de crítica gasta mais, mas qual o custo-benefício?
-   **Latência:** Tempo total até a resposta final.

### C. Alucinação (Hallucination)
-   **Import Error Rate:** O código importa libs que não estão no `requirements.txt` ou não existem?
-   **Function Call hallucination:** O agente tentou chamar uma tool que não existe?

## 4. Roteiro Passo a Passo (Mão na Massa)

### Setup Inicial (Hoje)
1.  Crie o virtualenv e instale `openai` (ou `langchain` se preferir abstração).
2.  Configure a chave da API no `.env`.
3.  Crie o arquivo `src/agents/critic.py`. Defina a classe `CriticAgent` que recebe um código e retorna um JSON: `{"approved": bool, "feedback": str}`.

### Criando o Loop
1.  Escreva um loop `while attempts < max_attempts`.
2.  Dentro, chame `analyst.generate()`.
3.  Chame `critic.evaluate(code)`.
4.  Se `approved == True`: `break` e retorne.
5.  Se `approved == False`: Adicione o feedback ao histórico do Analyst e rode o loop de novo.

### O Notebook
1.  Crie um dataset de 5 a 10 problemas de programação (ex: "Inverta uma lista", "Calcule fatorial", "Web scraper simples").
2.  Rode seu sistema nesses 10 problemas.
3.  Guarde os logs.
4.  No Pandas, carregue os logs e calcule as métricas acima.

## 5. Conteúdos Recomendados
-   **Paper:** "Self-Correction in LLMs" (Procure no arXiv).
-   **LangChain Docs:** Seção sobre "Extraction" e "Output Parsers" para garantir que seu Crítico devolva JSON estruturado.
-   **DeepLearning.ai:** Curso "Building Systems with ChatGPT API" (gratuito e curto) ensina bem essa parte de evaluation.

Boa sorte! Você tem tudo para executar isso em 3 dias se focar no MVP (Mínimo Produto Viável).
