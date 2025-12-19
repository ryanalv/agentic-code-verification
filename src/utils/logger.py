import logging
import sys
from src.config import settings

def setup_logger(name: str = "ai_docs_agent"):
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(settings.LOG_LEVEL)
        
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(settings.LOG_LEVEL)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File Handler (Optional, good for debugging)
        file_handler = logging.FileHandler(os.path.join(settings.DATA_DIR, "app.log"), encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

import os
# Initialize default logger
logger = setup_logger()
