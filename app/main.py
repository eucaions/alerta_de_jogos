from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

# Importações internas
from app.scheduler import iniciar_scheduler
from app.football_api import buscar_jogos_do_dia

# Configuração básica de log para facilitar o debug no terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Aplicação iniciando e agendando tarefas...")
    try:
        iniciar_scheduler()
        logger.info("✅ Scheduler configurado com sucesso!")
    except Exception as e:
        logger.error(f"❌ Falha ao iniciar o scheduler: {e}")
    
    yield
    
    logger.info("🛑 Aplicação encerrando")

app = FastAPI(lifespan=lifespan)

@app.get("/")
def home():
    return {
        "status": "online",
        "msg": "Sistema de Notificação de Jogos rodando",
        "documentacao": "/docs"
    }

@app.get("/teste-api")
def teste_api():
    jogos = buscar_jogos_do_dia()
    print(f"DEBUG JOGOS: {jogos}") # Olhe o terminal quando acessar essa rota
    return {"dados": jogos}