from fastapi import FastAPI, Request, Form
from fastapi.responses import FileResponse  
from contextlib import asynccontextmanager
import logging
from fastapi.templating import Jinja2Templates
from app.scheduler import iniciar_scheduler
from app.football_api import buscar_jogos_do_dia
from fastapi.middleware.cors import CORSMiddleware


templates = Jinja2Templates(directory="app/templates")

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():

    return FileResponse("app/templates/index.html")

@app.get("/api/jogos")
def pegar_jogos_json():
    jogos = buscar_jogos_do_dia()
    return {"dados": jogos}