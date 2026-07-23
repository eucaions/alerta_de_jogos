from fastapi import FastAPI, Request, Form
from fastapi.responses import FileResponse, RedirectResponse 
from contextlib import asynccontextmanager
import logging
from fastapi.templating import Jinja2Templates
from app.scheduler import iniciar_scheduler
from app.services.football_api import buscar_jogos_do_dia
from fastapi.middleware.cors import CORSMiddleware
from app.database.queries import listar_todos_os_times, atualizar_common_name_time

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



@app.get("/admin")
def painel_admin():
    """Entrega a página HTML do painel de controle"""
    return FileResponse("app/templates/admin.html")

@app.get("/api/times")
def api_listar_times():
    """Rota que o JavaScript vai chamar para listar os times na tela"""
    times = listar_todos_os_times()
    return {"times": times}

@app.post("/api/times/atualizar")
def api_atualizar_time(time_id: int = Form(...), common_name: str = Form(...)):
    """Recebe os dados do formulário e atualiza o banco"""
    try:
        atualizar_common_name_time(time_id, common_name)
        # Após atualizar, redireciona o usuário de volta para a página admin
        return RedirectResponse(url="/admin", status_code=303)
    except Exception as e:
        logger.error(f"Erro ao atualizar time: {e}")
        return {"status": "erro", "msg": str(e)}