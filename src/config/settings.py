import os
from dotenv import load_dotenv

load_dotenv()

API_OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DATA_DIR = os.getenv("DATA_DIR", "data")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)