# Utilitário de configuração de logs com suporte a contexto (passos e tokens).
# Permite rastrear o fluxo de execução e consumo de tokens através de ContextVars.
import logging
import sys
import contextvars
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Variáveis de Contexto para rastrear estado entre módulos sem passar argumentos
current_step = contextvars.ContextVar("current_step", default="Inicialização")
current_tokens = contextvars.ContextVar("current_tokens", default=0)

class ContextFilter(logging.Filter):
    """
    Injeta variáveis de contexto (passo, tokens) nos registros de log.
    """
    def filter(self, record):
        record.step = current_step.get()
        record.tokens = current_tokens.get()
        return True

def setup_logger(name: str = "agent_logger", log_file: str = "logs/application.log"):
    """
    Configura e retorna um logger com handlers de console e arquivo,
    usando um formato personalizado que inclui contexto global (passo, tokens).
    """
    # Cria diretório de logs se não existir
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Evita adicionar handlers múltiplas vezes se já configurado
    if logger.hasHandlers():
        return logger

    # Formato
    # Exemplo: 2023-10-27 10:00:00,123 | INFO     | Step: Analisando... | Tokens: 150    | Conteúdo da mensagem
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | Passo: %(step)-20s | Tokens: %(tokens)-6s | %(message)s'
    )

    # Filtro de Contexto
    ctx_filter = ContextFilter()
    logger.addFilter(ctx_filter)

    # Handler de Arquivo (Rotativo)
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    # Handler de Console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    return logger

# Instância global do logger
logger = setup_logger()

# Funções auxiliares para atualizar contexto
def set_step(step_name: str):
    return current_step.set(step_name)

def reset_step(token):
    current_step.reset(token)

def set_tokens(count: int):
    return current_tokens.set(count)

def add_tokens(count: int):
    current = current_tokens.get()
    return current_tokens.set(current + count)
