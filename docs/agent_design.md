# Documentação Técnica de Design: Agente Crítico

Esta documentação explica **como** o sistema funciona por baixo do capô. É destinada a desenvolvedores que querem entender a arquitetura e as decisões de código.

## 1. O Conceito: Arquitetura Ator-Crítico

Em sistemas de IA tradicionais, pedimos algo e aceitamos a primeira resposta (Architecture One-Shot). Isso é arriscado porque LLMs (chatbots) frequentemente alucinam (inventam fatos).

Este projeto implementa uma arquitetura de **Refinamento Iterativo**:
1. **Ator (Code Analyst)**: Tenta resolver o problema.
2. **Crítico (Critic Agent)**: Avalia a solução.
3. Se falhar, o Crítico explica o erro e o Ator tenta de novo.

---

## 2. Componentes do Sistema

### 2.1 Code Analyst (`src/code_analyst.py`)
- **Função**: Ler código e escrever documentação.
- **Ferramentas**: Pode ler arquivos do disco (`read_project_files`).
- **Comportamento**: É um agente "ReAct" (Reason + Act). Ele pensa ("Devo ler este arquivo"), age (lê o arquivo) e observa o resultado antes de escrever a resposta final.
- **Entrada de Feedback**: Recebe um parâmetro opcional `feedback`. Se preenchido, ele adiciona uma instrução extra ao seu prompt: "Atenção: Você errou X na vez anterior, corrija agora".

### 2.2 Critic Agent (`src/agents/critic.py`)
- **Função**: Garantia de Qualidade.
- **Não usa ferramentas externas**: Ele usa lógica de programação Python pura e chamadas de LLM para avaliação.
- **Método `check_hallucinations`**:
    - Usa **Expressões Regulares (Regex)** para encontrar todos os caminhos de arquivo citados no texto (ex: `src/main.py`).
    - Verifica fisicamente no disco (`os.path.exists`) se esses arquivos existem.
    - Se não existirem, marca como Alucinação. Isso é uma validação **determinística** (verdade absoluta), não depende da opinião da IA.
- **Método `evaluate_quality`**:
    - Envia o texto para um LLM (o juiz) com um prompt específico de avaliação.
    - O prompt pede uma nota de 0 a 10 baseada em critérios como: Clareza, Completude e Profundidade.
    - Retorna um JSON estruturado.

### 2.3 Servidor e Interface (`src/server.py`)
- **FastAPI**: Framework web usado para criar o servidor.
- **SSE (Server-Sent Events)**: Tecnologia usada para enviar dados em tempo real para o navegador. Ao inverso de uma requisição normal (que espera tudo ficar pronto para responder), o SSE mantém um canal aberto e envia cada log ("Pensando...", "Lendo arquivo...") assim que acontece.

### 2.4 Sistema de Logs e Contexto (`src/utils/logger.py`)
- **Problema**: Em sistemas complexos, é difícil saber qual "passo" lógico gerou um log específico.
- **Solução**: Uso de `contextvars`.
    - O módulo `logger.py` define variáveis de contexto (`current_step`, `current_tokens`).
    - Um `ContextFilter` injeta esses valores automaticamente em cada linha de log.
    - Isso permite logs ricos e contextuais sem poluir as assinaturas das funções.

---

## 3. Fluxo de Execução (O Loop)

Quando você clica em "Iniciar Análise":

1. O **Servidor** acorda e chama o gerador de análise.
2. **Iteração 0**:
   - O **Analista** é chamado. Ele lê os arquivos e produz o "Texto v1".
   - O **Crítico** recebe o "Texto v1".
   - O Crítico roda `check_hallucinations`: Encontrou erros?
   - O Crítico roda `evaluate_quality`: A nota é maior que 7?
3. **Decisão**:
   - **Se APROVADO**: O processo para e o texto é exibido em verde.
   - **Se REPROVADO**: 
     - O Crítico gera um texto de feedback (ex: "O arquivo ghost.py não existe.").
     - O loop começa a **Iteração 1**.
4. **Iteração 1**:
   - O **Analista** é chamado novamente, mas agora com o feedback do Crítico injetado no prompt.
   - Ele gera o "Texto v2" (teoricamente corrigido).
   - O Crítico avalia novamente.

Isso se repete até ser aprovado ou atingir o número máximo de tentativas (Max Retries), evitando loops infinitos e custos altos.

---

## 4. Decisões Técnicas Importantes

### Por que não usar apenas um prompt melhor?
Prompts melhores ajudam, mas não resolvem a "cegueira" da IA. A IA não sabe se um arquivo existe ou não. Apenas um código Python rodando no sistema operacional pode verificar a existência de um arquivo com 100% de certeza. Por isso, a ferramenta de verificação de alucinação é código, não IA.

### Por que JSON na saída da IA?
Pedir para a IA responder em JSON (`response_format={"type": "json_object"}`) permite que nosso código Python leia a resposta de forma programática (extraia a nota, o feedback) sem precisar tentar "adivinhar" onde está a resposta no meio de um texto longo.

### Por que FastAPI e não Flask/Django?
FastAPI é moderno, muito rápido e tem suporte nativo a operações assíncronas (`async/await`), o que é crucial para streaming de dados (SSE) e para não travar o servidor enquanto a IA está "pensando".

---

## 5. Glossário para Iniciantes

- **LLM**: Large Language Model (o cérebro da IA, tipo GPT-4, Claude, Kimi).
- **Alucinação**: Quando a IA inventa uma informação falsa com total confiança.
- **Mock**: Uma simulação. Quando não temos a chave da API, usamos "Mock" para fingir que a IA respondeu, permitindo testar o resto do sistema.
- **Token**: A unidade de custo da IA. Basicamente, pedaços de palavras. Quanto mais texto, mais tokens, mais caro.
