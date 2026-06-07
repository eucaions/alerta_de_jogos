from apscheduler.schedulers.background import BackgroundScheduler
from app.telegram_bot import enviar_mensagem
from app.football_api import buscar_jogos_do_dia
from app.message_formatter import formatar_lista_jogos

scheduler = BackgroundScheduler()

def verificar_jogos():

    print("🔎 Verificando jogos...")

    jogos = buscar_jogos_do_dia() 

    if not jogos:
        print("ℹ️ Nenhum jogo encontrado para enviar.")
        return

    mensagem = formatar_lista_jogos(jogos)
    enviar_mensagem(mensagem)

def iniciar_scheduler():

    print("🚀 Iniciando scheduler...")

    scheduler.add_job(
        verificar_jogos,
        "cron",
        hour=6,
        minute=0,
        timezone="America/Sao_Paulo"
    )

    scheduler.start()

    print("✅ Scheduler iniciado!")