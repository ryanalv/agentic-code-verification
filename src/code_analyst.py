from src.agents.react_core import ReActAgent
from src.utils.file_tools import read_project_files
import os

def analyze_codebase(project_path: str, project_name: str, feedback: str = None) -> dict:
    """
    Inicia um agente ReAct para analisar uma base de código local.
    """
    tools = {
        "read_project_files": read_project_files
    }
    
    agent = ReActAgent(tools=tools)
    
    goal = f"""
    Você é um Arquiteto de Software Sênior especializado em análise de código e documentação técnica. 
    Sua missão é realizar uma análise profunda do projeto [project_name] e gerar documentação técnica completa e estruturada. 
    Sua responsabilidade é compreender completamente como o sistema funciona e comunicar isso de forma clara, precisa e acessível.
         1. Comece lendo os arquivos usando read_project_files("{project_path}"). 
         2. Identifique o propósito geral do projeto, a linguagem de programação, tecnologias principais e padrões arquiteturais utilizados.
         3. Trace como os dados fluem através do sistema, incluindo entrada, processamento e saída.
         4.Consolide todas as informações em narrativas claras e crie um diagrama Mermaid que represente a arquitetura.
         A documentação deve ser entregue em Markdown com as seguintes seções, nesta ordem:
         Visão Geral do Projeto: Resuma o propósito, funcionalidades principais e contexto de negócio.
      Tecnologias e Dependências: Liste as tecnologias, frameworks, bibliotecas e versões relevantes.
      Arquitetura do Sistema: Descreva a arquitetura geral, padrões de design e estrutura organizacional.
      Fluxo de Execução com Diagrama: Explique passo a passo como o sistema executa desde o ponto de entrada até a lógica principal. Inclua um diagrama Mermaid que visualize este fluxo.
      Componentes Chave: Para cada componente importante, descreva: nome, responsabilidade, interfaces públicas (funções/métodos principais) e interações com outros componentes.
      Fluxo de Dados: Documente como os dados são recebidos, processados e entregues através dos diferentes componentes.
      Configuração e Uso: Inclua instruções inferidas do código sobre como configurar e executar o projeto, incluindo pré-requisitos, instalação e exemplos de uso.
      Dependências Entre Módulos: Crie um diagrama ou descrição das relações de dependência entre os principais módulos.
      Características da Documentação
      Use linguagem técnica precisa, mas acessível para desenvolvedores com diferentes níveis de experiência.
      Seja específico: cite nomes reais de classes, funções e arquivos do projeto.
      Use exemplos concretos extraídos do código quando apropriado.
      Organize a informação hierarquicamente, do geral para o específico.
      Mantenha toda a documentação rigorosamente em Português Brasileiro.
      Formate o Markdown de forma profissional com destaques, listas e estrutura clara.

    """
    
    if feedback:
        goal += f"\n\nATENÇÃO - FEEDBACK DE CRÍTICA ANTERIOR:\n{feedback}\nPor favor, corrija os pontos acima na nova documentação."

    return agent.run(goal)
