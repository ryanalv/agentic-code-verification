# Script de teste para validação do sistema de logs e contexto.
# Verifica se os logs estão sendo gerados corretamente com as informações de passo e tokens.
import sys
import os
import contextvars
import logging
from pathlib import Path

# Adiciona a raiz do projeto ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logger import logger, set_step, set_tokens, add_tokens, current_step, current_tokens

def test_logger():
    print("Testando Logger...")
    
    # 1. Limpa log antigo
    log_file = Path("logs/application.log")
    if log_file.exists():
        # backup ou apenas nota
        pass

    # 2. Define Contexto
    set_step("Passo-Teste-1")
    set_tokens(100)
    
    # 3. Registra Log
    logger.info("Esta é uma mensagem de teste do script de verificação.")
    
    add_tokens(50)
    logger.debug("Mensagem de debug com mais tokens.")
    
    # 4. Verifica Contexto
    assert current_step.get() == "Passo-Teste-1"
    assert current_tokens.get() == 150
    
    print("Variáveis de contexto verificadas na memória.")
    
    # 5. Verifica Conteúdo do Arquivo
    # Permitimos algum tempo para flush se necessário, mas rotating file handler geralmente é imediato
    if not log_file.exists():
        print(f"Erro: Arquivo de log {log_file} não encontrado.")
        return
        
    content = log_file.read_text(encoding='utf-8')
    print(f"Comprimento do conteúdo do log: {len(content)}")
    
    if "Passo-Teste-1" in content and "Tokens: 150" in content:
        print("SUCESSO: Arquivo de log contém passo e tokens esperados.")
    else:
        print("FALHA: Arquivo de log faltando dados de contexto.")
        print("Trecho do conteúdo:", content[-500:])

if __name__ == "__main__":
    test_logger()
