# agentic-code-verification
AI Quality Critic Agent: Loop de Reflexão para Code Analysis
Este projeto implementa um Agente Crítico de IA projetado para monitorar, validar e iterar sobre os outputs de um agente analista de código. O objetivo é garantir a precisão técnica e reduzir alucinações através de um fluxo autônomo de revisão e feedback.

🚀 O Problema
Sistemas de IA de passo único (one-shot) frequentemente falham em lógica complexa ou geram código com erros sintáticos. Este projeto resolve isso aplicando o padrão de Arquitetura Critic-Actor, onde o resultado só é entregue se passar pelo crivo de um segundo agente especializado em qualidade.

🛠️ Arquitetura do Sistema
O fluxo de trabalho segue um loop de controle fechado:

Analyst Agent: Recebe o prompt e gera a análise/código inicial.

Critic Agent: Analisa o output com base em ferramentas de execução e regras de negócio.

Loop de Feedback: Se o Crítico detectar falhas, ele gera um log de erros e solicita a re-execução (até o limite de iterações definido).

Entrega Final: Output validado ou relatório de erro crítico.

📊 Métricas de Engenharia
Diferente de projetos simples, este repositório foca em métricas reais de performance de LLM:

Pass Rate: Porcentagem de sucesso antes e depois da intervenção do crítico.

Token Efficiency: Custo computacional versus ganho de qualidade.

Hallucination Rate: Identificação de chamadas de bibliotecas inexistentes via ferramentas de introspecção.

📁 Estrutura do Projeto
src/: Core logic do agente crítico e ferramentas de validação.

notebooks/: Análise estatística de custos, tokens e qualidade.

docs/: Documentação das decisões arquiteturais e lições aprendidas.

🛠️ Tecnologias
Python 3.10+

OpenAI API / LangChain

Pandas & Matplotlib (Análise de Métricas)

Standard Logging (Rastreabilidade)
