# Manual do Projeto: Verificação de Código Agentica

## 1. Visão Geral do Projeto
Este projeto é um sistema de **Auditoria Automatizada de Documentação**. Ele utiliza Agentes de IA para ler uma documentação técnica, compará-la com o código-fonte real, e emitir um relatório de qualidade e veracidade (detectando "alucinações" ou arquivos inexistentes).

A arquitetura do projeto evoluiu para **Hexagonal (Ports & Adapters)** combinada com **PraisonAI (Hierárquica)**. Isso garante que o sistema seja robusto, escalável para grandes projetos e fácil de manter.

## 2. A Arquitetura Hexagonal (Explicação Conceitual)

Imagine o projeto como uma cebola com camadas. As camadas de dentro não sabem que as de fora existem.

### Camada 1: O Núcleo (Core Domain) - O "Coração"
Aqui vivem as regras do jogo. Elas não mudam se trocarmos a IA ou o Banco de Dados.
- **Entidades**: O que é um "Resultado de Revisão"?
- **Portas**: Interfaces que definem *como* o mundo deve falar com a gente.

### Camada 2: Aplicação (Use Cases) - O "Maestro"
Aqui vivem os fluxos. O Maestro diz: "Pegue a IA, analise isso, e me dê o resultado".

### Camada 3: Infraestrutura (Adapters) - O "Mundo Real"
Aqui vivem as conexões com ferramentas externas. É aqui que o PraisonAI, OpenAI e o Sistema de Arquivos residem. Eles se "adaptam" para plugar no Núcleo.

---

## 3. Explicação Detalhada dos Arquivos

### 🟠 Camada Central (Core)

#### `src/core/domain/entities.py`
*   **O que é**: Define os objetos de dados puros.
*   **Papel**: Contém a classe `ReviewResult`. Ela garante que, não importa qual IA estamos usando, o resultado final sempre terá `score`, `approved`, e `hallucinations`.
*   **Impacto**: Se você quiser adicionar um novo campo no relatório (ex: "tempo_execucao"), edite aqui.

#### `src/core/ports/critic_port.py`
*   **O que é**: O Contrato (Interface).
*   **Papel**: Define a classe abstrata `ICriticAgent`. Ela diz: "Qualquer agente crítico deve ter um método `review`".
*   **Impacto**: Permite trocar o PraisonAI pelo CrewAI sem quebrar o resto do sistema.

#### `src/core/use_cases/verify_docs.py`
*   **O que é**: A Lógica de Negócio.
*   **Papel**: Recebe um Agente Crítico (qualquer um) e executa a revisão.
*   **Impacto**: Centraliza a regra de negócio. "Verificar documentação" é uma ação deste arquivo.

### 🔵 Camada de Infraestrutura (Adapters)

#### `src/infrastructure/adapters/praison_critic.py`
*   **O que é**: A Implementação Real (O "Plugin").
*   **Papel**: Aqui está toda a mágica da **PraisonAI**.
    *   Cria os agentes (`SectionCritic` e `LeadCritic`).
    *   Faz o Split do texto.
    *   Roda a verificação hierárquica.
*   **Impacto**: É a "Cola" do sistema. É quem você chama para rodar o processo.

#### `src/pipelines/review_pipeline.py`
*   **O que é**: O Ponto de Entrada (Composition Root).
*   **Papel**: Conectar tudo. Ele instancia o Adapter (`PraisonCriticAdapter`) e injeta dentro do Caso de Uso (`VerifyDocumentationUseCase`).
*   **Impacto**: É a "Cola" do sistema. É quem você chama para rodar o processo.

#### `src/utils/text_splitter.py`
*   **O que é**: Utilitário de Suporte.
*   **Papel**: Quebra Markdown gigante em capítulos.
*   **Impacto**: Vital para permitir análise de projetos grandes.

---

## 4. Fluxo de Dados (Como funcina na prática)

1.  O Usuário chama `ReviewPipeline.run()`.
2.  A Pipeline chama `VerifyDocumentationUseCase.execute()`.
3.  O Caso de Uso chama `PraisonCriticAdapter.review()`.
4.  O Adapter:
    *   Usa `text_splitter` para fatiar o texto.
    *   Cria agentes PraisonAI para cada fatia.
    *   Executa a varredura (`check_files_existence`).
    *   Retorna um JSON.
5.  O Adapter converte o JSON para `ReviewResult` (Entidade).
6.  O resultado volta borbulhando até o usuário.

## 5. Por que isso é vantajoso?

1.  **Independência**: Se a OpenAI cair e quisermos usar Llama local, criamos um `LlamaCriticAdapter` e plugamos. O Core nem fica sabendo.
2.  **Testabilidade**: Podemos testar o `VerifyDocumentationUseCase` com um "Agente Falso" (Mock) que não gasta dinheiro.
3.  **Organização**: Cada arquivo tem uma responsabilidade única e clara. O código não vira uma "macarronada".
