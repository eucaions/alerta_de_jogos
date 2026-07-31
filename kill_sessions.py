import os
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

if TOKEN:
    print("🧹 Forçando encerramento de todas as instâncias e conexões ativas no Telegram...")
    url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true"
    res = requests.get(url)
    print("Resposta do Telegram:", res.json())
else:
    print("❌ TELEGRAM_TOKEN não encontrado!")