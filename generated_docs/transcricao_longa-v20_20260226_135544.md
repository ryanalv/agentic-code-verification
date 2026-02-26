# Documentação Técnica Oficial – Projeto `transcricao_longa-v2.0`

---

## 1. Visão Geral

O `transcricao_longa-v2.0` é uma plataforma avançada para transcrição automática de vídeos longos, enriquecida com identificação de falantes, revisão textual, sumarização e integração com serviços de nuvem. O sistema foi desenvolvido para atender fluxos robustos, tolerantes a falhas, escaláveis e auditáveis, seguindo os mais rigorosos padrões de engenharia de software.

Seu núcleo utiliza **Arquitetura Hexagonal (Ports and Adapters)**, desacoplando domínio, aplicação e infraestrutura, permitindo fácil manutenção, testes e evolução tecnológica. O processamento pode ser local (CLI) ou distribuído (via Dramatiq/Redis), com persistência local (SQLite), checkpointing intermediário, logging contextualizado e integração com Google Speech-to-Text, Gemini LLM e Google Cloud Storage.

---

## 2. Tecnologias, Componentes e Padrões

### 2.1. Tecnologias

- **Python 3.10+**
- **FFmpeg**: Processamento de mídia (chunking, extração de áudio/vídeo)
- **Google Speech-to-Text V2 (Chirp 3)**
- **Google Gemini 2.5 (Pro/Flash)**
- **Google Cloud Storage (GCS)**
- **SQLite**: Persistência local
- **Dramatiq + Redis**: Orquestração de filas e processamento distribuído
- **Logging contextualizado**: Logs por job, em terminal e arquivos

### 2.2. Padrões e Arquitetura

- **Arquitetura Hexagonal (Ports and Adapters)**
- **Idempotência e Checkpointing**
- **Batching Inteligente**
- **Resiliência a Falhas**
- **Injeção de Dependências via Fábrica**
- **Integração CLI e Fila**

---

## 3. Contexto Teórico da Arquitetura

### 3.1. Arquitetura Hexagonal (Ports and Adapters)

**Conceito**:  
A Arquitetura Hexagonal, ou Ports and Adapters, propõe que o núcleo do sistema (domínio e regras de negócio) seja isolado das dependências externas (bancos, APIs, UI). As "Portas" definem contratos; "Adaptadores" implementam esses contratos para interagir com o mundo externo.

**Aplicação no Projeto**:  
- **Portas**: Definem contratos para processamento de mídia, STT, LLM, storage, persistência, filesystem.
- **Adaptadores**: Implementam portas para FFmpeg, Google STT, Gemini, GCS, SQLite, etc.
- **Orquestrador**: Controla o pipeline, orquestrando portas e garantindo idempotência.

### 3.2. Processamento Distribuído com Dramatiq/Redis

**Conceito**:  
Permite escalabilidade horizontal, desacoplando submissão e processamento de jobs via filas. Workers podem ser escalados conforme demanda.

**Aplicação no Projeto**:  
- **Submissão**: Jobs são enviados via fila Dramatiq.
- **Consumo**: Workers processam jobs, garantindo tolerância a falhas e retomada.

### 3.3. Checkpointing e Idempotência

**Conceito**:  
Salvar o estado intermediário do processamento permite retomada após falhas, garantindo que cada etapa seja executada apenas uma vez.

**Aplicação no Projeto**:  
- **Checkpoints**: Salvos em disco a cada etapa.
- **Idempotência**: Etapas validam se já foram executadas antes de rodar novamente.

### 3.4. Logging Contextualizado

**Conceito**:  
Logs detalhados por contexto/job facilitam troubleshooting, auditoria e análise de erros.

**Aplicação no Projeto**:  
- **Logs por job**: Terminal e arquivos separados.
- **ContextVars**: Garante contexto correto mesmo em execução concorrente.

---

## 4. Diagrama Arquitetural

### 4.1. Visão Geral do Sistema

|           CLI            |        Fila Dramatiq       |
|-------------------------|----------------------------|
|         main.py         |    processar_entrada.send  |
|           |             |          |                 |
|           v             |          v                 |
|      +-------------------------------------+         |
|      |          Orquestrador               |         |
|      +-------------------------------------+         |
|        |      |      |      |      |      |         |
|   Chunk |  STT |  LLM | Storage | Repo | FS         |
|    |        |      |      |      |      |           |
|   v        v      v      v      v      v            |
| FFmpeg  Google  Gemini  GCS  SQLite  LocalFS        |
|         STT                                       |

### 4.2. Fluxo de Dados

| Etapa            | Descrição                                                                 |
|------------------|--------------------------------------------------------------------------|
| Submissão        | Usuário envia vídeo via CLI ou fila                                      |
| Persistência     | Job registrado no SQLite, checkpoint inicial                             |
| Chunking         | FFmpeg divide vídeo, extrai áudios, envia ao GCS                        |
| STT              | Google STT transcreve áudios em lote                                     |
| Revisão/LLM      | Gemini revisa texto, diariza, sumariza                                   |
| Salvamento       | Artefatos finais salvos local/GCS                                        |
| Limpeza          | Artefatos temporários removidos                                          |
| Logging          | Logs detalhados por etapa/job                                            |

---

## 5. Análise Detalhada dos Componentes

### 5.1. main.py (CLI)

#### 5.1.1. Função `main()`

- **Responsabilidade**:  
  Ponto de entrada do sistema. Realiza parsing de argumentos, inicializa logging, carrega variáveis de ambiente, valida arquivos, submete jobs e exibe status.

- **Fluxo Passo a Passo**:
  1. Carrega variáveis de ambiente do `.env`.
  2. Inicializa logger contextualizado.
  3. Faz parsing dos argumentos CLI:
      - `--video`: Caminho do vídeo para transcrição.
      - `--case_id`: Identificador do caso (opcional).
      - `--force_restart`: Reinicia job, sobrescrevendo estado anterior.
      - `--status`: Exibe status de jobs.
      - `--retomar`, `--refazer`, `--completo`: Controle de jobs.
  4. Se `--status`, chama `exibir_status(args)` e encerra.
  5. Valida existência do vídeo.
  6. Loga submissão.
  7. Submete job via `processar_entrada.send`.
  8. Gera ID do job (hash MD5 do nome do arquivo).
  9. Informa usuário sobre submissão, ID e instruções.

- **Casos de Erro**:
  - Falha ao inicializar DB: exibe aviso.
  - Arquivo de vídeo não encontrado: loga erro, encerra.
  - Falha ao submeter job: loga erro, encerra.

- **Pseudocódigo**:
  ```
  if args.status:
      exibir_status(args)
      exit
  if not video_exists(args.video):
      log_erro
      exit
  processar_entrada.send(args.video, args.force_restart)
  print(job_id)
  ```

#### 5.1.2. Função `exibir_status(args)`

- **Responsabilidade**: Exibe status detalhado ou lista de jobs.
- **Fluxo**:
  1. Inicializa DB.
  2. Se `args.status` é string (ID), busca detalhes do job.
  3. Senão, lista até 20 jobs recentes.
  4. Exibe mensagens de erro se necessário.

#### 5.1.3. Integração

- Integra com:
  - `src/workers/entrada.py` (fila Dramatiq)
  - `src/infraestrutura/job_store.py` (persistência)
  - `src/infraestrutura/logging.py` (logging)

---

### 5.2. src/aplicacao/orquestrador.py

#### 5.2.1. Classe `Orquestrador`

- **Responsabilidade**:  
  Service Facade do pipeline. Expõe métodos para cada etapa, controla fluxo, idempotência, checkpointing, logging e integração entre portas/adaptadores.

- **Principais Métodos Públicos**:
  - `submeter_video`
  - `executar_pipeline`
  - `executar_chunking`
  - `executar_stt`
  - `executar_revisao_diarizacao`
  - `executar_revisao_final_condicional`
  - `executar_sumarizacao`
  - `executar_salvamento`
  - `executar_limpeza`

- **Fluxo de Execução**:
  1. Registrar job no SQLite.
  2. Inicializar diretórios e checkpoint.
  3. Para cada etapa:
      - Verifica se já foi executada (idempotência).
      - Executa lógica.
      - Salva checkpoint.
      - Atualiza status.
      - Loga erros/progresso.

- **Exemplo Prático**:
  ```python
  orq = Orquestrador(...)
  job_id = orq.submeter_video("/caminho/video.mp4")
  orq.executar_pipeline(job_id)
  ```

- **Tradeoffs**:
  - Checkpointing em disco local aumenta resiliência, mas pode causar inconsistências em ambientes distribuídos.
  - Idempotência evita duplicidade, mas requer lógica extra.

- **Casos de Erro**:
  - Falha em etapa: status "ERRO", logs detalhados, checkpoint preservado.
  - Falha ao salvar checkpoint: log de aviso, pipeline tenta prosseguir.
  - Falha de pré-requisito: etapa não executada, log de aviso.

---

### 5.3. src/aplicacao/interfaces.py

- **Portas/Contratos**:
  - `VideoProcessingPort`: Chunking, extração de áudio/vídeo, duração.
  - `SttPort`: Transcrição em lote.
  - `LlmPort`: Revisão textual, diarização, sumarização, verificação de qualidade.
  - `StoragePort`: Upload/limpeza de arquivos.
  - `RepositoryPort`: Persistência de jobs/eventos.
  - `FileSystemPort`: Manipulação de arquivos locais.

- **Decisão Arquitetural**:
  - Toda integração externa deve implementar estas interfaces, garantindo desacoplamento.

---

### 5.4. src/infraestrutura/* (Adaptadores)

- **FFmpegAdapter**: Implementa `VideoProcessingPort` (chunking, extração via FFmpeg).
- **SttChirp3Adapter**: Implementa `SttPort` (Google Speech-to-Text V2).
- **GeminiAdapter**: Implementa `LlmPort` (Gemini 2.5 Pro/Flash).
- **GCSAdapter**: Implementa `StoragePort` (Google Cloud Storage).
- **SQLiteAdapter**: Implementa `RepositoryPort` (SQLite).
- **LocalFileSystemAdapter**: Implementa `FileSystemPort` (disco local).

---

### 5.5. src/infraestrutura/job_store.py

- **Funções**:
  - `inicializar_db`: Cria tabelas e índices.
  - `criar_job`, `atualizar_status`, `concluir_job`: Gerencia ciclo de vida do job.
  - `obter_job`, `listar_jobs`: Consulta.
  - `registrar_evento`: Logging de eventos.
  - `estatisticas`: Estatísticas agregadas.

- **Locking**:  
  Uso de `threading.Lock` para concorrência segura.

- **Limitações**:  
  Não recomendado para ambientes clusterizados.

---

### 5.6. src/filas/broker.py e src/filas/externa.py

- **Broker**:  
  Configuração do Dramatiq (Redis).
- **consumir_job_externo**:  
  Ator Dramatiq que consome mensagens JSON, submete jobs, retorna status.

---

### 5.7. src/infraestrutura/logging.py

- **Logger Contextualizado**:  
  Logs por job, terminal e arquivos.
- **Utilitários**:  
  `log_info`, `log_erro`, `log_aviso`, `log_progresso`, `log_sucesso`.
- **ContextVars**:  
  Logging correto em ambientes concorrentes.

---

## 6. Fluxo de Dados Detalhado

```plaintext
Usuário executa main.py
  |
  |---> Valida argumentos, inicializa logging, carrega env
  |---> Se status: exibe lista/detalhe de jobs
  |---> Se vídeo: registra job no SQLite, cria diretórios, salva checkpoint
  |---> Submete job via fila Dramatiq (processar_entrada.send)
          |
          |---> Worker consome, instancia Orquestrador
                  |
                  |---> Executa pipeline:
                         - Chunking (FFmpeg)
                         - STT (Google)
                         - Revisão/Diarização/Sumarização (Gemini)
                         - Salvamento (local/GCS)
                         - Limpeza
                  |---> Atualiza status/checkpoint/logs
  |---> Usuário pode consultar status a qualquer momento
  |---> Artefatos finais disponíveis local/GCS
```

---

## 7. Contratos Públicos

- **CLI**:  
  Função `main()`, `exibir_status(args)`
- **Orquestrador**:  
  Métodos públicos para cada etapa
- **Portas/Interfaces**:  
  Contratos para todos os adaptadores externos
- **Adaptadores**:  
  Implementações para FFmpeg, STT, LLM, GCS, SQLite, Filesystem
- **Logging**:  
  Funções utilitárias
- **Persistência**:  
  Criação, atualização, consulta, listagem de requisitos
- **Fila**:  
  `processar_entrada.send`, `consumir_job_externo`

---

## 8. Exemplos Práticos

### Submissão via CLI

```bash
python main.py --video /caminho/video.mp4 --case_id 12345
```

### Consulta de Status

```bash
python main.py --status
python main.py --status <job_id>
```

### Execução Local do Pipeline

```python
from src.factory import criar_orquestrador
orq = criar_orquestrador()
job_id = orq.submeter_video("/caminho/video.mp4")
orq.executar_pipeline(job_id)
```

---

## 9. Riscos, Limitações e Tradeoffs

### Riscos

- Dependência de serviços externos (Google STT, Gemini, GCS)
- SQLite como gargalo em alta concorrência
- Falhas no upload/download GCS
- Parsing de respostas LLM pode falhar
- Variáveis de ambiente ausentes causam falhas silenciosas
- Jobs grandes podem exceder limites de memória/tempo
- Locking global do SQLite pode causar contenção

### Limitações

- SQLite não é adequado para ambientes distribuídos de larga escala
- FFmpeg deve estar instalado no ambiente
- Checkpointing depende de disco local
- Não há API HTTP/REST exposta
- Sem rollback transacional completo
- Sem autenticação/autorização na CLI
- Sem versionamento embutido de modelos/prompts

### Tradeoffs

- SQLite facilita setup local, mas limita escalabilidade
- Hexagonal aumenta testabilidade, mas adiciona complexidade
- Checkpoint local aumenta resiliência, mas pode causar inconsistências
- Batching reduz custos, mas pode aumentar latência de jobs individuais
- Dramatiq/Redis permite escalabilidade, mas adiciona dependências externas

---

## 10. Diagrama ASCII (Tabela)

|      CLI/Main      |           |         Orquestrador         |           |    Adaptadores (Ports)      |           | Infraestrutura Externa      |
|--------------------|-----------|-----------------------------|-----------|-----------------------------|-----------|----------------------------|
| User Input         |   --->    |  submeter_video             |   --->    | VideoProcessingPort         |   --->    | FFmpeg                     |
| (main.py)          |           |  executar_pipeline          |           | SttPort                     |           | Google Speech-to-Text      |
|                    |           |  executar_chunking          |           | LlmPort                     |           | Gemini                     |
|                    |           |  executar_stt               |           | StoragePort                 |           | GCS                        |
|                    |           |  executar_revisao_diarizacao|           | RepositoryPort              |           | SQLite                     |
|                    |           |  executar_sumarizacao       |           | FileSystemPort              |           | Local FileSystem           |
|                    |           |  executar_salvamento        |           |                             |           |                            |
|                    |           |  executar_limpeza           |           |                             |           |                            |
|                    |           |  logging (por job)          |           |                             |           |                            |
|                    |           |  checkpointing              |           |                             |           |                            |

---

## 11. Considerações Finais

O projeto foi desenhado para máxima robustez, extensibilidade e facilidade operacional, com separação clara de responsabilidades. Recomenda-se, para produção/escala, migrar o backend de persistência, adicionar autenticação/autorização e versionamento de modelos.

**Esta documentação é exaustiva e cobre todos os contratos, fluxos, decisões e tradeoffs do sistema. Consulte seções específicas para detalhes de implementação, exemplos práticos, fluxos de dados e diagramas.**

---

**FIM DA DOCUMENTAÇÃO**

(Aviso: Esta documentação atingiu o limite de refinamentos e pode conter imprecisões.)