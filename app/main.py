from fastapi import FastAPI, Request, Form
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from contextlib import asynccontextmanager
import logging
from fastapi.templating import Jinja2Templates
from app.scheduler import iniciar_scheduler
from fastapi.middleware.cors import CORSMiddleware
from app.database.queries import listar_todos_os_times, obter_favoritos_ids_usuario, obter_ou_criar_usuario_por_telegram, salvar_favoritos_usuario

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

""" @app.get("/api/jogos")
def pegar_jogos_json():
    jogos = buscar_jogos_do_dia()
    return {"dados": jogos}
 """


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
        """ atualizar_common_name_time(time_id, common_name) """
        # Após atualizar, redireciona o usuário de volta para a página admin
        return RedirectResponse(url="/admin", status_code=303)
    except Exception as e:
        logger.error(f"Erro ao atualizar time: {e}")
        return {"status": "erro", "msg": str(e)}

# 1. Rota GET: Carrega a página (opcionalmente com o chat_id na URL)
@app.get("/favoritos", response_class=HTMLResponse)
@app.get("/favoritos/{telegram_chat_id}", response_class=HTMLResponse)
def view_selecionar_favoritos(request: Request, telegram_chat_id: str = ""):
    todos_os_times = listar_todos_os_times()
    favoritos_atuais = []

    # Se já passou o telegram_chat_id na URL, busca os favoritos existentes
    if telegram_chat_id:
        user_id = obter_ou_criar_usuario_por_telegram(telegram_chat_id)
        if user_id:
            favoritos_atuais = obter_favoritos_ids_usuario(user_id)

    return templates.TemplateResponse(
        request=request,
        name="select_favorites.html",
        context={
            "telegram_chat_id": telegram_chat_id,
            "todos_os_times": todos_os_times,
            "favoritos_atuais": favoritos_atuais
        }
    )


# 2. Rota POST: Recebe o ID do Telegram + Times Selecionados e grava no banco
@app.post("/favoritos/salvar", response_class=HTMLResponse)
def salvar_favoritos(
    request: Request,
    telegram_chat_id: str = Form(...),
    team_ids: list[int] = Form(default=[])
):
    # 1. Garante que o usuário existe na tabela 'users' e recupera o ID interno
    user_id = obter_ou_criar_usuario_por_telegram(telegram_chat_id.strip())

    sucesso = False
    if user_id:
        # 2. Salva as escolhas na tabela 'user_favorites'
        sucesso = salvar_favoritos_usuario(user_id, team_ids)

    todos_os_times = listar_todos_os_times()
    favoritos_atuais = obter_favoritos_ids_usuario(user_id) if user_id else []

    mensagem = "Configurações e favoritos salvos com sucesso!" if sucesso else "Erro ao salvar dados."

    return templates.TemplateResponse(
        request=request,
        name="select_favorites.html",
        context={
            "telegram_chat_id": telegram_chat_id,
            "todos_os_times": todos_os_times,
            "favoritos_atuais": favoritos_atuais,
            "mensagem_sucesso": mensagem
        }
    )