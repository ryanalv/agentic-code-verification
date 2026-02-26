# Documentação Técnica Profunda e Exaustiva do Pipeline `transcricao_longa-v2.0`

---

## 1. Visão Geral

O projeto **transcricao_longa-v2.0** é um sistema robusto para transcrição automática de vídeos extensos, como audiências judiciais, utilizando uma arquitetura moderna, modular e resiliente. O pipeline permite processamento assíncrono, escalável e tolerante a falhas, integrando serviços de IA (Google Gemini, Chirp3 STT) e infraestrutura de nuvem (Google Cloud Storage, Redis/Dramatiq).  
O sistema é **idempotente**: cada etapa pode ser reexecutada sem efeitos colaterais, com persistência de estado e checkpoints, permitindo recuperação e retomada de jobs mesmo após falhas.  
A operação pode ser feita via CLI, API ou filas externas, e é altamente configurável por variáveis de ambiente.

---

## 2. Tecnologias Utilizadas

- **Python 3.10+**
- **Arquitetura Hexagonal** (Ports & Adapters)
- **Dramatiq** (processamento assíncrono via Redis)
- **Google Cloud Storage** (armazenamento de artefatos)
- **Google Gemini 2.5 Pro/Flash** (LLM multimodal)
- **Google Speech-to-Text V2 (Chirp3)**
- **FFmpeg** (chunking e extração de mídia)
- **SQLite** (persistência de jobs)
- **Logging contextualizado** (por job, arquivo e terminal)
- **dotenv** (configuração via arquivo .env)
- **Dataclasses, Enum, Protocols** (tipagem forte e contratos)

---

## 3. Contexto Teórico da Arquitetura

### 3.1. Arquitetura Hexagonal (Ports & Adapters)

**Conceito**:  
A arquitetura hexagonal (também chamada de Ports & Adapters) propõe uma separação clara entre o núcleo de negócio (domínio) e as interfaces externas (infraestrutura), permitindo fácil substituição de componentes externos sem afetar a lógica central.

**Aplicação no Projeto**:  
- **Domínio**: Entidades e regras de negócio puras.
- **Aplicação**: Orquestração do pipeline, casos de uso, interfaces (ports).
- **Infraestrutura**: Adapters para serviços externos (GCS, Gemini, STT, FFmpeg, Filesystem, Job Store, Logging).
- **Drivers**: CLI, Workers Dramatiq, consumidores de fila externa.

**Benefícios**:  
- Fácil manutenção e testes.
- Flexibilidade para trocar serviços externos.
- Robustez e desacoplamento.

---

### 3.2. Processamento Assíncrono e Distribuído

**Conceito**:  
O uso de filas de mensagens (Dramatiq/Redis) permite escalar o processamento horizontalmente, distribuindo jobs entre múltiplos workers.

**Aplicação no Projeto**:  
- Workers Dramatiq processam jobs em background.
- Jobs são persistidos e podem ser retomados após falhas.

---

### 3.3. Idempotência e Persistência de Estado

**Conceito**:  
Cada etapa do pipeline pode ser executada múltiplas vezes sem efeitos colaterais, graças à persistência de checkpoints e estado.

**Aplicação no Projeto**:  
- Checkpoints salvos em disco e banco SQLite.
- Jobs podem ser retomados ou reiniciados.

---

### 3.4. Diagrama ASCII da Arquitetura Hexagonal

```markdown
|---------------------------|
|         CLI/API           |
|---------------------------|
          |
          v
|---------------------------|
|      Orquestrador         |
|---------------------------|
      /   |   |   |   \
     /    |   |   |    \
    v     v   v   v     v
|--------|--------|--------|--------|--------|
| FFmpeg | Chirp3 | Gemini | GCS    | SQLite |
|--------|--------|--------|--------|--------|
      |        |        |        |        |
      v        v        v        v        v
|------Infraestrutura------|
| Filesystem | Logging     |
|--------------------------|
```

---

## 4. Análise de Código Detalhada

### 4.1. main.py (Ponto de Entrada CLI)

#### Funções Principais

- **_maybe_load_dotenv()**: Carrega variáveis de ambiente do `.env`.
- **exibir_status(args)**: Exibe status detalhado de jobs, consultando o banco SQLite.
- **main()**: Parser de argumentos CLI, inicializa logger, valida arquivo, submete job para worker Dramatiq, exibe ID do job.

#### Fluxo de Execução Passo a Passo

1. Usuário executa `python main.py --video "/caminho/video.mp4"`.
2. Carrega variáveis de ambiente, inicializa logger.
3. Exibe status se solicitado.
4. Valida existência do vídeo.
5. Submete job para fila de processamento.
6. Exibe ID do job e instruções.

#### Casos de Erro

- Falha ao inicializar banco.
- Arquivo de vídeo não encontrado.
- Falha ao submeter job.

#### Pseudocódigo

```python
def main():
    load_dotenv()
    args = parse_args()
    logger = init_logger()
    if args.status:
        exibir_status(args)
        return
    if not file_exists(args.video):
        logger.error("Arquivo não encontrado")
        return
    job_id = processar_entrada.send(args)
    print(f"Job submetido: {job_id}")
```

#### Integração

- Depende de `src.workers.entrada.processar_entrada`.
- Usa logging centralizado.
- Consulta jobs via `src.infraestrutura.job_store`.

---

### 4.2. src/factory.py (Fábrica de Orquestrador)

- **criar_orquestrador()**: Instancia o Orquestrador principal, injetando todos os adapters necessários.
- **Decisão**: Centraliza a construção do pipeline, facilitando testes e substituição de componentes.

---

### 4.3. src/aplicacao/interfaces.py (Ports)

Define contratos (`Protocol`) para todos os adapters:

- **VideoProcessingPort**: Planejamento de chunks, extração de áudio/vídeo, cálculo de duração.
- **SttPort**: Transcrição batch, suporte a múltiplos idiomas e diarização.
- **LlmPort**: Revisão textual, diarização, sumarização, verificação de qualidade.
- **StoragePort**: Upload e limpeza de arquivos em blob storage.
- **RepositoryPort**: Persistência e consulta de jobs e eventos.
- **FileSystemPort**: Operações de arquivo e diretório locais.

---

### 4.4. src/aplicacao/orquestrador.py (Orquestrador Principal)

#### Classe `Orquestrador`

- **Responsabilidade**: Orquestra todo o pipeline.
- **Métodos Públicos**:
  - `submeter_video`
  - `executar_pipeline`
  - `executar_chunking`
  - `executar_stt`
  - `executar_revisao_diarizacao`
  - `executar_revisao_final_condicional`
  - `executar_sumarizacao`
  - `executar_salvamento`
  - `executar_limpeza`

#### Fluxo de Execução Passo a Passo

1. **Chunking**: Divide vídeo em chunks usando FFmpeg, priorizando silêncios.
2. **STT**: Transcreve áudios dos chunks em batches.
3. **Revisão/Diarização**: Agrupa chunks para revisão multimodal via Gemini.
4. **Revisão Final**: Loop de auto-correção, verifica qualidade, executa revisão pesada se necessário.
5. **Sumarização**: Gera resumo estruturado.
6. **Salvamento**: Persiste artefatos finais.
7. **Limpeza**: Remove arquivos temporários.

#### Pseudocódigo Simplificado

```python
def executar_pipeline(job_id):
    executar_chunking(job_id)
    executar_stt(job_id)
    executar_revisao_diarizacao(job_id)
    executar_revisao_final_condicional(job_id)
    executar_sumarizacao(job_id)
    executar_salvamento(job_id)
    executar_limpeza(job_id)
```

#### Casos de Erro

- Falha em qualquer etapa: status do job atualizado para ERRO, erro persistido e logado.
- Falha ao carregar checkpoint: loga aviso, tenta continuar.
- Falha em upload/download: loga aviso, pode interromper etapa.

#### Integração

- Depende de todas as portas (adapters).
- Usa logging contextualizado.
- Persistência via checkpoints e banco.

---

### 4.5. src/infraestrutura/job_store.py (Persistência de Jobs)

- **Banco SQLite**: Armazena jobs, status, progresso, eventos e estatísticas.
- **Funções**:
  - `inicializar_db`
  - `criar_job`, `atualizar_status`, `concluir_job`
  - `obter_job`, `listar_jobs`, `obter_eventos`
  - `formatar_status_job`
- **Thread-safe**: Uso de locks para evitar corrupção.
- **Adapter**: `SQLiteAdapter` implementa `RepositoryPort`.

---

### 4.6. src/infraestrutura/ffmpeg.py (Processamento de Vídeo)

- **FFmpegAdapter**: Implementa `VideoProcessingPort`.
- **Funções**:
  - `planejar_chunks`: Divide vídeo em chunks, priorizando silêncios.
  - `extrair_audio`, `extrair_video`
  - `get_duracao_media`
- **Tradeoff**: Chunking baseado em silêncio melhora qualidade, mas pode ser mais lento.

---

### 4.7. src/infraestrutura/gcs.py (Armazenamento Cloud)

- **GCSAdapter**: Implementa `StoragePort`.
- **Funções**:
  - `upload_arquivo`
  - `limpar_diretorio`
  - `download_arquivo`, `download_json`, `verificar_existe`, `listar_blobs`

---

### 4.8. src/infraestrutura/gemini.py (LLM Multimodal)

- **GeminiAdapter**: Implementa `LlmPort`.
- **Funções**:
  - `revisar_e_diarizar`
  - `revisar_final`
  - `verificar_qualidade`
  - `sumarizar`
- **Robustez**: Retries automáticos para erros transitórios e parsing de JSON.

---

### 4.9. src/infraestrutura/filesystem.py (Filesystem Local)

- **LocalFileSystemAdapter**: Implementa `FileSystemPort`.
- **Funções**:
  - `salvar_arquivo`, `ler_arquivo`, `criar_diretorio`, `existe`
- **Limitação**: Não suporta storage distribuído nativamente.

---

### 4.10. src/infraestrutura/stt_chirp3.py (STT)

- **SttChirp3Adapter**: Implementa `SttPort`.
- **Funções**:
  - `transcrever_lote`
- **Tradeoff**: Processamento em lote reduz custos, mas pode aumentar uso de memória.

---

### 4.11. src/filas/broker.py e src/filas/externa.py (Filas Dramatiq)

- **Broker**: Configuração do Dramatiq com Redis.
- **consumir_job_externo**: Ator Dramatiq para consumir jobs de fila externa.

---

## 5. Fluxos de Dados e Execução

### 5.1. Diagrama ASCII do Pipeline

```markdown
| CLI/API/Fila Externa |
          |
          v
|---Orquestrador---|
|   |   |   |   |   |
v   v   v   v   v   v
FFmpeg  Chirp3  Gemini  GCS  SQLite  Filesystem
```

### 5.2. Fluxo Detalhado

1. Usuário submete vídeo via CLI ou fila externa.
2. Orquestrador gera job_id, verifica existência, registra job e salva checkpoint inicial.
3. Pipeline executa etapas sequenciais:
   - Chunking
   - STT
   - Revisão/Diarização
   - Revisão Final
   - Sumarização
   - Salvamento
   - Limpeza
4. Resultados intermediários são persistidos.
5. Erros tratados, logados e status do job atualizado.
6. Artefatos finais salvos, job marcado como concluído.

---

## 6. Exemplos Práticos

### Submissão de Job via CLI

```bash
python main.py --video "/caminho/video.mp4" --case_id "12345"
```

### Consulta de Status

```bash
python main.py --status
python main.py --status <job_id>
```

### Retomada ou Reinício

```bash
python main.py --video "/caminho/video.mp4" --retomar
python main.py --video "/caminho/video.mp4" --force_restart
```

---

## 7. Casos de Erro e Recuperação

- **Falha de serviço externo**: Retries automáticos, logs detalhados, status do job atualizado para ERRO.
- **Interrupção de worker/processo**: Estado salvo, permitindo retomada.
- **Falha de parsing LLM**: Retries limitados, logs de erro, job pode ser reiniciado.
- **Arquivo de vídeo inacessível**: Job não iniciado, erro logado.
- **Corrupção de checkpoint**: Log de aviso, pipeline tenta continuar.

---

## 8. Decisões Arquiteturais, Tradeoffs e Limitações

### Decisões Arquiteturais

- Arquitetura Hexagonal para desacoplamento e manutenção.
- Divisão clara entre domínio, aplicação e infraestrutura.
- Injeção de dependências via portas.
- Persistência de estado local e SQLite.
- Processamento assíncrono via Dramatiq/Redis.
- Logging contextualizado por job.

### Tradeoffs

- Persistência local facilita recuperação, mas dificulta cluster/distribuído.
- SQLite é simples, mas não escala para múltiplos nós concorrentes.
- Etapas idempotentes aumentam robustez, mas adicionam complexidade.
- Processamento em batches reduz custos, mas pode limitar paralelismo.
- Logging detalhado facilita auditoria, mas pode gerar muitos arquivos.

### Limitações

- Pipeline depende de serviços Google Cloud; não funciona offline.
- Persistência de checkpoints é local ao nó; pode haver inconsistências em clusters.
- Arquivos de vídeo devem estar acessíveis localmente.
- Granularidade dos chunks é fixa por configuração.
- Não há retry automático para falhas de hardware ou corrupção de arquivos locais.
- FileSystemPort assume operações locais.
- Recuperação de jobs depende da integridade dos arquivos de checkpoint e banco.
- Lógica de sumarização depende da qualidade do LLM.
- Não há controle de acesso/autenticação.
- Não suporta múltiplos idiomas simultâneos por job.

---

## 9. Contratos Públicos

- **main.py**: CLI para submissão e consulta de jobs.
- **src/aplicacao/interfaces.py**: Contratos para todos os adapters.
- **src/aplicacao/orquestrador.py**: API de orquestração do pipeline.
- **src/infraestrutura/job_store.py**: API para persistência e consulta de jobs.
- **src/infraestrutura/filesystem.py**: API para operações de arquivo/diretório.
- **src/infraestrutura/gcs.py**: API para integração com Google Cloud Storage.
- **src/infraestrutura/ffmpeg.py**: API para processamento de mídia.
- **src/infraestrutura/gemini.py**: API para integração com LLM Gemini.
- **src/infraestrutura/stt_chirp3.py**: API para integração com Chirp3 STT.
- **src/factory.py**: Fábrica para instanciar o Orquestrador.

---

## 10. Integração com Outras Partes do Sistema

- **CLI/API**: Interface de entrada para submissão e consulta de jobs.
- **Workers Dramatiq**: Executam etapas do pipeline em background.
- **Google Cloud**: Armazenamento de artefatos, processamento de IA.
- **Banco SQLite**: Persistência de jobs, eventos e progresso.
- **Filesystem Local**: Persistência de checkpoints e artefatos finais.
- **Logging**: Observabilidade e auditoria detalhada.

---

## 11. Riscos e Mitigações

### Riscos

- Dependência de serviços externos (GCS, Gemini, STT).
- Jobs longos podem ser interrompidos por falhas de infraestrutura.
- Persistência local pode ser problemática em ambientes distribuídos.
- Erros de parsing LLM podem interromper o pipeline.
- Concorrência e consistência de estado em múltiplos workers.
- Limitações de quota e rate limit dos serviços Google.
- Falhas no upload/download de arquivos para GCS.
- Jobs podem ficar "zumbis" na fila.
- Configurações incorretas de ambiente.

### Mitigações

- Retries automáticos para serviços externos.
- Persistência de checkpoints e logs detalhados.
- Validação de pré-requisitos e idempotência.
- Logging contextualizado e auditoria.
- Configuração centralizada via .env.

---

## 12. Diagrama ASCII do Fluxo de Job

```markdown
| Usuário/Externo | 
        |
        v
|  CLI/API/Filas  |
        |
        v
|  Orquestrador   |
        |
        v
|-----------------------------|
| Chunking | STT | Revisão/Diarização |
| Revisão Final | Sumarização | Salvamento | Limpeza |
|-----------------------------|
        |
        v
| Persistência (SQLite, Filesystem, GCS) |
        |
        v
| Logs e Auditoria |
```

---

## 13. Explicações Didáticas e Analogias

- **Arquitetura Hexagonal**: Imagine uma central de controle (domínio/aplicação) com várias portas. Cada porta pode ser conectada a um serviço externo diferente (internet, telefone, rádio). Assim, se um serviço falhar ou precisar ser substituído, basta trocar a porta/adaptador, sem mexer na central.
- **Idempotência**: Como um botão de "salvar" que pode ser pressionado várias vezes sem duplicar o arquivo.
- **Chunking por Silêncio**: Como cortar um livro em capítulos sempre que há uma pausa, facilitando a leitura e compreensão.

---

## 14. Conclusão

Esta documentação exaustiva detalha todos os componentes, fluxos, contratos, decisões, riscos, tradeoffs e limitações do sistema transcricao_longa-v2.0.  
Desenvolvedores de todos os níveis e stakeholders não-técnicos encontrarão explicações claras, exemplos práticos, diagramas visuais e contexto suficiente para implementar, manter e evoluir o sistema sem acesso ao código-fonte original.  
**Toda a riqueza de detalhes das análises setoriais foi consolidada e explicitada, garantindo a implementação correta e segura do pipeline.**

---

**Fim da Documentação Técnica Oficial**

(Aviso: Esta documentação atingiu o limite de refinamentos e pode conter imprecisões.)