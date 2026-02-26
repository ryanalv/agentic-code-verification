# Tutorial: Utilizando a CLI do Agente Crítico

Como a Interface Web (`src/server.py`) foi temporariamente desabilitada, as análises de código agora devem ser executadas **nativamente pelo terminal** através do novo utilitário de Linha de Comando (`cli.py`).

## Requisitos Iniciais
Certifique-se de que o seu ambiente virtual Python está ativado e que as variáveis de ambiente necessárias (`OPENAI_API_KEY`, etc.) estão configuradas na sua sessão do terminal ou no arquivo `.env`.

- **Para ativar o ambiente (Windows):**
  ```powershell
  .\.venv\Scripts\activate
  ```

## Como Executar a Análise

A sintaxe básica para executar o script a partir da raiz do projeto (`agentic-code-verification`) é:

```powershell
python cli.py <caminho_do_projeto> [opções]
```

### Exemplo 1: Análise Simples
Para analisar um projeto localizado em `C:\Projetos\MeuApp`:

```powershell
python cli.py "C:\Projetos\MeuApp"
```

### Exemplo 2: Utilizando o RAG (Conhecimento de Domínio)
Se você quer fornecer o contexto extra do Domínio de Negócios / Arquitetura (arquivos com regras do seu projeto) para a IA embutir na documentação:

```powershell
python cli.py "C:\Projetos\MeuApp" --domain "C:\Projetos\RegrasDeNegocio"
```
*(Você também pode usar a flag mais curta `-d` no lugar de `--domain`)*

### Exemplo 3: Analisando o próprio código (Self-Analysis)
Para testar a ferramenta analisando o código-fonte dela mesma (tudo dentro da pasta `src`), basta executar sem argumentos apontando para `.` (diretório atual):

```powershell
python cli.py .
```

## Onde encontrar os Resultados?
Durante a execução, você verá os logs processuais no seu Terminal, informando que o Analista e o Crítico iniciaram suas assinaturas.

Quando a documentação passar nas verificações do Agente Crítico, o arquivo em formato Markdown (`.md`) será salvo na pasta `generated_docs` dentro do seu diretório atual:

📂 `agentic-code-verification\generated_docs\MeuApp_20260224_103000.md`

Basta abrir esse arquivo utilizando o VSCode ou seu visualizador Markdown favorito!
