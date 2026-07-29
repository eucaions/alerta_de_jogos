from apscheduler.schedulers.background import BackgroundScheduler
from app.services.football_api import schedule_fixtures
from app.services.scraper import msg_por_fixture
from app.telegram_bot import disparar_agenda_matinal_usuarios

# Instancia o agendador único
scheduler = BackgroundScheduler()

def job_03am_carga_api():
    """
    [03:00] Busca na API oficial todas as partidas do dia e salva na tabela 'fixtures'.
    """
    print("🌙 [03:00] Executando carga diária de jogos da API...")
    try:
        schedule_fixtures()
        print("✅ [03:00] Jogos do dia salvos na tabela fixtures com sucesso!")
    except Exception as e:
        print(f"❌ [03:00] Erro na carga diária da API: {e}")


def rotina_matinal_jogos():
    """
    [08:00] Executa o scraper de transmissões, atualiza os site_names no banco, 
    monta a mensagem unificada e envia a agenda do dia para todos os usuários.
    """
    print("🌅 [08:00] Iniciando rotina matinal de processamento e envio de jogos...")
    try:
        # 1. Scraping + Atualização do Banco + Geração do Mapa { team_api_id: "mensagem" }
        mensagens_por_time = msg_por_fixture()
        
        # 2. Se houver partidas mapeadas, envia para os favoritos de cada usuário
        if mensagens_por_time:
            disparar_agenda_matinal_usuarios(mensagens_por_time)
            print("✅ [08:00] Agenda de jogos enviada aos usuários com sucesso!")
        else:
            print("ℹ️ [08:00] Nenhuma mensagem a ser disparada hoje.")
    except Exception as e:
        print(f"❌ [08:00] Erro na rotina matinal de envio: {e}")


def iniciar_scheduler():
    print("🚀 Configurando agendador de tarefas...")

    # TAREFA 1: Carga dos jogos na API às 03:00 da manhã
    scheduler.add_job(
        job_03am_carga_api,
        "cron",
        hour=3,
        minute=0,
        timezone="America/Sao_Paulo"
    )

    # TAREFA 2: Scraping + Formatação + Disparo da Agenda às 08:00 da manhã
    scheduler.add_job(
        rotina_matinal_jogos,
        "cron",
        hour=8,
        minute=0,
        timezone="America/Sao_Paulo"
    )

    scheduler.start()
    print("✅ Scheduler em execução com sucesso!")