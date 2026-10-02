import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

if not WEBHOOK_SECRET:
    raise ValueError("WEBHOOK_SECRET não encontrado. Defina no .env")