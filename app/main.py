import threading
import logging
import time
from telebot.apihelper import ApiTelegramException
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.scheduler import iniciar_scheduler
from app.telegram_bot import bot
from app.database.queries import (
    listar_todos_os_times,
    obter_favoritos_ids_usuario,
    obter_ou_criar_usuario_por_telegram,
    salvar_favoritos_usuario
)

templates = Jinja2Templates(directory="app/templates")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def rodar_bot_telegram():
    """Roda a escuta do bot em background no Uvicorn Worker."""
    logger.info("🤖 Thread do Bot do Telegram iniciada.")
    
    while True:
        try:
            if not bot:
                logger.warning("⚠️ Bot não configurado.")
                break
                
            logger.info("🤖 Limpando webhooks e iniciando polling continuo...")
            bot.remove_webhook()
            # Usa polling simples em loop ao inves de infinity_polling para evitar bloqueio no Uvicorn
            bot.polling(non_stop=True, interval=1, timeout=20)

        except ApiTelegramException as e:
            if e.error_code == 409:
                logger.warning("⚠️ Conflito 409 (Outra instância rodando). Aguardando 5s...")
                time.sleep(5)
            else:
                logger.error(f"❌ Erro da API do Telegram ({e.error_code}): {e}")
                time.sleep(5)
        except Exception as e:
            logger.error(f"❌ Erro no polling: {e}")
            time.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ==========================================
    # ON STARTUP: Inicia Scheduler e Bot Telegram
    # ==========================================
    logger.info("🚀 Aplicação iniciando...")
    
    # 1. Configura o Scheduler de envio matinal
    try:
        iniciar_scheduler()
        logger.info("✅ Scheduler configurado com sucesso!")
    except Exception as e:
        logger.error(f"❌ Falha ao iniciar o scheduler: {e}")

    # 2. Inicia o Bot do Telegram em background
    if bot:
        thread_bot = threading.Thread(target=rodar_bot_telegram, daemon=True)
        thread_bot.start()
    else:
        logger.warning("⚠️ Bot do Telegram não instanciado (TELEGRAM_TOKEN ausente).")

    yield

    # ==========================================
    # ON SHUTDOWN: Encerra conexões limpas
    # ==========================================
    logger.info("🛑 Aplicação encerrando")
    if bot:
        bot.stop_bot()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )


@app.get("/admin")
def painel_admin():
    """Entrega a página HTML do painel de controle"""
    return FileResponse("app/templates/admin.html")


@app.get("/api/times")
def api_listar_times():
    """Rota que o JavaScript chama para listar os times na tela"""
    times = listar_todos_os_times()
    return {"times": times}


@app.post("/api/times/atualizar")
def api_atualizar_time(time_id: int = Form(...), common_name: str = Form(...)):
    """Recebe os dados do formulário e atualiza o banco"""
    try:
        # atualizar_common_name_time(time_id, common_name)
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
    user_id = obter_ou_criar_usuario_por_telegram(telegram_chat_id.strip())

    sucesso = False
    if user_id:
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