<div align="center">
  <img src="https://img.shields.io/badge/Status-Ativo-brightgreen" alt="Status" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue" alt="Python Version" />
  <img src="https://img.shields.io/badge/AI-Agentic%20Workflow-purple" alt="Architecture" />
  <img src="https://img.shields.io/badge/LLM-Azure%20OpenAI-blue" alt="Provider" />
</div>

<br>

<div align="center">
  <h1>🤖 Agentic Code Verification</h1>
  <p><b>Uma plataforma geradora de documentação técnica inteligente baseada em Arquitetura de Múltiplos Agentes Autônomos (Multi-Agent RAG System).</b></p>
</div>

---

## 📖 O que é este projeto? (Para todos os públicos)

### A Analogia Simples (Para iniciantes e estudantes 🎓)
Imagine que entender um código gigante escrito por outra pessoa é como tentar ler um livro em chinês sem dicionário. 

Este projeto constrói um **time de especialistas virtuais (Agentes de Inteligência Artificial)** liderados por um Gerente Exigente. O time funciona assim:
1. O **Explorador:** Entra na pasta do seu código e mapeia todos os arquivos que existem.
2. O **Planejador:** Olha os arquivos e decide: *"Ok, para entender esse sistema, precisamos ler o arquivo A e B primeiro."*
3. O **Leitor:** Lê as regras de negócio da empresa e o código-fonte em si.
4. O **Escritor:** Escreve uma documentação gigante, com diagramas de texto, explicando passo a passo o que o código faz.
5. O **Crítico (O Chefe chato):** Pega a documentação do Escritor e diz: *"Nota 6. Você esqueceu de explicar como os erros são tratados na linha 42 e seus diagramas estão ruins. Refaça!"*

O Escritor só pode entregar o projeto para você quando o Crítico aprovar. No final, você recebe um documento em Markdown perfeito explicando o seu sistema!

### A Visão Técnica (Para Engenheiros e Seniores 💻)
O **Agentic Code Verification** é um pipeline *ReAct (Reasoning and Acting)* orquestrado via Grafos de Estado (State Graph). Ao invés de usar um único LLM com um prompt gigante, o sistema delega responsabilidades para agentes especializados.

- **Arquitetura Base:** LangGraph/StateGraph para roteamento condicional inteligente.
- **Domínio/Contexto:** Suporte a **RAG (Retrieval-Augmented Generation)** utilizando o ChromaDB. Permite injetar arquivos de arquitetura (Domain Knowledge) fora do código-fonte para que a IA documente o projeto respeitando as premissas da empresa.
- **PraisonAI Adapter:** Utiliza hierarquia de agentes (Worker/Manager) no nó de Crítica para avaliar a profundidade técnica, penalizando abstrações excessivas e detectando alucinações de arquivos (arquivos inventados na explicação).
- **LLM Integrado:** Configurado nativamente para utilizar a infraestrutura segura da **Azure OpenAI** (modelos da família GPT-4).

---

## ✨ Funcionalidades Principais

- 🕵️ **Análise de Contexto Estendida (RAG):** Mistura a leitura do código puro com as regras de negócio escritas em Markdown da sua empresa.
- 📐 **Geração de Diagramas ASCII Obrigatórios:** A IA desenha o Fluxo de Dados e a Arquitetura em tabelas ASCII no meio da documentação sem depender de ferramentas visuais externas.
- 🔁 **Workflow Auto-Corretivo (Self-Healing):** Se a documentação ficar superficial (ex: não descrever tratamento de erros), o sistema entra em *loop* e reescreve as seções penalizadas pelo *Critic Agent*.
- 🎯 **Conformidade de Arquivos:** Previne a "alucinação clássica" de LLMs, verificando diretamente no disco via hooks python se os arquivos referenciados pela IA realmente existem.

---

## 🚀 Guia de Instalação Rápida

### Pré-requisitos
- **Python 3.10 ou superior** (`python --version`)
- **Git**
- Uma conta/chave ativa da **Azure OpenAI**.

### 1. Clonando e Preparando o Ambiente
Abra o seu terminal (Prompt de Comando ou PowerShell) e execute:

```bash
# Clone o repositório
git clone https://github.com/ryanalv/agentic-code-verification.git
cd agentic-code-verification

# Crie um ambiente virtual (Recomendado)
python -m venv .venv

# Ative o ambiente (No Windows)
.\.venv\Scripts\activate

# Instale todas as bibliotecas necessárias
pip install -r requirements.txt
```

### 2. Configurando as Credenciais (O Arquivo `.env`)
O sistema precisa de chaves para conversar com o cérebro da Inteligência Artificial.
Crie um arquivo chamado `.env` na pasta raiz do projeto e preencha com suas credenciais da Azure:

```properties
AZURE_OPENAI_API_KEY="sua-chave-aqui"
AZURE_OPENAI_ENDPOINT="https://seu-recurso.openai.azure.com/"
AZURE_OPENAI_API_VERSION="2024-02-15-preview"
AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o"  # Ou o nome do seu deployment
```

---

## 🖥️ Como Usar (Via Linha de Comando - CLI)

Para rodar a ferramenta, utilizamos o script inteligente `cli.py`. Todo processo agora corre via terminal.

### Opção A: Analisando uma pasta simples
Você quer gerar a documentação de um app que está no seu disco C:
```bash
python cli.py "C:\Projetos\MeuApp"
```

### Opção B: Análise Profunda com RAG (Conhecimento de Domínio)
Você tem uma pasta com as "Regras do Negócio" ou "Manuais de Arquitetura", e quer que a IA leia isso antes de avaliar o código:
```bash
python cli.py "C:\Projetos\MeuApp" --domain "C:\Projetos\RegrasDeNegocio"
```

### Opção C: Auto-Análise (Self-Analysis)
Para testar a inteligência do sistema, você pode pedir para ele documentar e explicar o *próprio código fonte* dele mesmo:
```bash
python cli.py .
```

### 📂 Onde fica o resultado?
Sente, pegue um café ☕ (isso pode demorar de 2 a 5 minutos dependendo de quantas vezes o Agente Crítico mandar o Agente Escritor refazer o trabalho).

Quando finalizar, acesse a pasta gerada automaticamente:
`agentic-code-verification/generated_docs/`

Lá dentro haverá um arquivo Markdown lindamente formatado (ex: `MeuApp_20260226_105000.md`) com a documentação exaustiva do projeto!

---

## 🧠 Arquitetura Interna: A Vida de uma Execução

Para os famintos por conhecimento de base arquitetural, eis o fluxo de vida do dado dentro do LangGraph (`src/agents/workflow.py` e `src/agents/react_core.py`):

1. **`Scanner Node`**: Recebe o path inicial. Faz varredura de S.O. (os.walk) levantando metadados de até mil arquivos.
2. **`Planner Node`**: Atua como o Arquiteto Pai. Filtra dependências de sistema (`node_modules`, `venv`) e seleciona estritamente os arquivos relevantes aos fluxos de negócio. Transforma a lista de arquivos estruturada num plano de execução tático.
3. **`Reader Node`**: Abre I/O no disco e lê o código-fonte fisicamente. Em paralelo, orquestra consultas à Base Vetorial (ChromaDB) caso a flag `--domain` seja acionada, misturando AST de código com heurísticas corporativas.
4. **`Writer Node`**: Um mini Map-Reduce interno. Fatia o contexto em pedaços e roda N instâncias simultâneas de sub-LLMs para gerar rascunhos em paralelo. Uma instância "Master" junta os pedaços num markdown coeso, formatado, e com injeção de diagramas de fluxo de dados.
5. **`Critic Node`**: Dispara uma bateria estruturada com a engine `PraisonAI`. Instancia 1 `Section_Critic` e 1 `Lead_Critic`. O Lead consolida notas (0 a 10). Se a nota base for `< 8.0` ou se as seções de *Tradeoffs*, *Limites* e *Arquitetura* estiverem superficiais, a documentação falha (Return: `Approved=False`).
6. **`Loop (Ciclo de Vida)`**: O sistema roteia de volta para as ferramentas de geração caso o Crítico descarte o material, perpetuando iterações até o esgotamento do limite máximo.

---

## 🤝 Contribuindo

Se você é estudante, sinta-se à vontade para ler os códigos em `src/agents/specialized/` para aprender como os Prompts de IA são construídos profissionalmente!

Se você é Sênior e quiser incluir provedores Groq/Ollama/Anthropic nativos, pull requests são mais que bem-vindos.

*"Documentação não precisa ser dolorosa. Ela só precisa ser delegada para quem não dorme."* 🦾
