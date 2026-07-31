import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Form, Response, status
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.scheduler import iniciar_scheduler
import app.telegram_bot as telegram_module
from app.telegram_bot import bot, processar_update_telegram
from app.database.queries import (
    listar_todos_os_times,
    obter_favoritos_ids_usuario,
    obter_ou_criar_usuario_por_telegram,
    salvar_favoritos_usuario
)

templates = Jinja2Templates(directory="app/templates")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 [LIFESPAN] Aplicação iniciando...")
    
    # 1. Configura o Scheduler de envio matinal
    try:
        iniciar_scheduler()
        logger.info("✅ [LIFESPAN] Scheduler configurado com sucesso!")
    except Exception as e:
        logger.error(f"❌ [LIFESPAN] Falha ao iniciar o scheduler: {e}")

    # 2. Registra o WEBHOOK do Telegram apontando para a URL pública no Render
    base_url = os.getenv("APP_URL", "https://jogos-alert-web.onrender.com").rstrip("/")
    webhook_url = f"{base_url}/telegram-webhook"

    if bot and getattr(bot, 'token', None):
        try:
            logger.info(f"🔗 Registrando Webhook no Telegram: {webhook_url}")
            bot.remove_webhook()
            bot.set_webhook(url=webhook_url)
            logger.info("✅ Webhook registrado com sucesso!")
        except Exception as e:
            logger.error(f"❌ Falha ao registrar Webhook: {e}")
    else:
        logger.error("❌ Bot não configurado (TELEGRAM_TOKEN ausente).")

    yield

    logger.info("🛑 [LIFESPAN] Aplicação encerrando...")
    if bot and getattr(bot, 'token', None):
        try:
            bot.remove_webhook()
            logger.info("✅ Webhook removido no encerramento.")
        except Exception as e:
            logger.error(f"⚠️ Erro ao remover webhook: {e}")


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


# 📍 ROTA DO WEBHOOK: Recebe as atualizações do Telegram via HTTP POST
@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    """Recebe as mensagens enviadas pelos usuários no Telegram via Webhook HTTP."""
    try:
        json_data = await request.json()
        logger.info(f"📩 Webhook recebido: {json_data}")
        processar_update_telegram(json_data)
        return Response(status_code=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"❌ Erro ao processar Webhook: {e}")
        return Response(status_code=status.HTTP_400_BAD_REQUEST)


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