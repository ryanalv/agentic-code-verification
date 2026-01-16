# 🤖 Agente Crítico de Qualidade de IA

Bem-vindo ao projeto **AI Quality Critic Agent**. Este é um sistema inteligente projetado para garantir que o código e a documentação gerados por Inteligência Artificial sejam precisos, úteis e livres de erros.

---

## 📖 O que é este projeto?

Imagine que você tem um estagiário júnior (vamos chamá-lo de **Code Analyst**) que escreve documentações de software. Ele é rápido, mas às vezes inventa coisas (alucinações) ou esquece detalhes importantes.

Este projeto cria um **Supervisor Sênior** (o **Critic Agent**) para revisar o trabalho desse estagiário.
1. O **Analista** faz o trabalho.
2. O **Crítico** revisa, dá uma nota e aponta erros (como arquivos que não existem).
3. Se o trabalho for ruim, o Crítico devolve para o Analista corrigir.
4. Isso se repete até o trabalho ficar excelente.

---

## ✨ Funcionalidades Principais

- **Interface Web Moderna**: Visualize todo o processo em tempo real no seu navegador.
- **Detecção de Alucinação**: O sistema verifica automaticamente se os arquivos citados pela IA realmente existem no seu projeto.
- **Avaliação de Qualidade**: Um "Juiz de IA" dá uma nota de 0 a 10 para a clareza e completude do texto.
- **Auto-Correção**: O sistema tenta corrigir erros automaticamente refazendo a tarefa com base no feedback.

---

## 🚀 Guia de Instalação (Passo a Passo)

Siga estes passos se você nunca rodou um projeto Python antes.

### Pré-requisitos
- **Python 3.10 ou superior** instalado. (Digite `python --version` no terminal para verificar).
- **Git** instalado.

### 1. Preparar o Ambiente

Abra o seu terminal (Prompt de Comando ou PowerShell) e navegue até a pasta do projeto:
```bash
cd "c:\Projetos Estudos\Agentes IA\agentic-code-verification\ai-quality-critic-agent"
```

Instale as dependências necessárias (bibliotecas que o projeto usa):
```bash
pip install -r requirements.txt
```
*Se você receber erros de permissão ou "pip not found", verifique a instalação do seu Python.*

### 2. Configurar a Chave de API

Este projeto usa Inteligência Artificial (LLMs) via OpenRouter. Você precisa de uma chave de acesso.

1. Encontre o arquivo chamado `.env` na pasta do projeto.
2. Abra-o com um editor de texto (Bloco de Notas ou VS Code).
3. Procure por `OPENROUTER_API_KEY`.
4. Coloque sua chave logo após o igual, sem aspas. Exemplo:
   ```properties
   OPENROUTER_API_KEY=sk-or-v1-seu-token-aqui
   ```
5. Salve o arquivo.

**Nota:** Se você não tiver uma chave, o sistema rodará em **Modo de Simulação (Mock)**, gerando dados de teste para você ver a interface funcionando.

---

## 🖥️ Como Usar

### Executando a Interface Web (Recomendado)

1. No terminal, execute:
   ```bash
   python src/server.py
   ```
2. Você verá uma mensagem como `Uvicorn running on http://0.0.0.0:8000`.
3. Abra seu navegador (Chrome, Edge, etc.) e acesse: [http://localhost:8000](http://localhost:8000)
4. Clique no botão azul **"▶ Iniciar Análise"**.
5. Acompanhe os logs e a prévia da documentação aparecendo na tela.

### Executando Análise de Métricas (Avançado)

Se você quer ver gráficos e dados estatísticos:
1. Abra a pasta `notebooks` no VS Code.
2. Abra o arquivo `metrics_analysis.ipynb`.
3. Clique no botão "Run All" ou execute as células uma por uma.

---

## 📂 Estrutura do Projeto

Para você se localizar:

- **`src/`**: Onde fica todo o código fonte.
  - **`agents/`**: O cérebro da IA.
    - `critic.py`: O agente supervisor (Critico).
    - `react_core.py`: O motor que faz a IA "pensar" e usar ferramentas.
    - `code_analyst.py`: O agente operário (Analista).
  - **`web/`**: Arquivos da interface visual (HTML).
  - `server.py`: O servidor que conecta a interface ao código Python.
  - **`utils/`**: Utilitários e helpers.
    - `logger.py`: Sistema de logs avançado com contexto (passos e tokens).
- **`docs/`**: Documentação técnica detalhada.
- **`notebooks/`**: Experimentos e análises de dados.
- **`tests/`**: Scripts para testar se tudo está funcionando.

---

## ❓ Resolução de Problemas Comuns

- **Erro: "API Key environment variable not set"**:
  - Você esqueceu de configurar o arquivo `.env` ou esqueceu de reiniciar o servidor após salvar o arquivo.

- **Erro: "Module not found"**:
  - Você esqueceu de rodar `pip install -r requirements.txt`.

- **A interface não abre**:
  - Verifique se o terminal está aberto e rodando o comando `python src/server.py` sem erros.

---
*Desenvolvido como parte do estudo de Agentes de IA Autônomos.*
