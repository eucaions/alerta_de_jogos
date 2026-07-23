from apscheduler.schedulers.background import BackgroundScheduler
from app.database.queries import obter_todos_usuarios_com_favoritos
from app.services.scraper import msg_por_fixture
from app.telegram_bot import disparar_agenda_matinal_usuarios, enviar_mensagem
from app.services.football_api import buscar_jogos_do_dia, schedule_fixtures
from app.message_formatter import formatar_lista_jogos
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import conectar_banco 
from app.telegram_bot import enviar_alerta_telegram


scheduler = BackgroundScheduler()



scheduler = BackgroundScheduler()

def verificar_e_enviar_alertas_proximos_jogos():
    print("🔎 [Worker] Verificando se há jogos começando agora para enviar alertas...")
    
    conn = conectar_banco()
    cursor = conn.cursor()
    
    query = """
        SELECT 
            f.id AS fixture_id,
            f.home_team,
            f.away_team,
            f.name_league,
            u.telegram_chat_id
        FROM fixtures f
        JOIN teams t_home ON (f.home_team = t_home.api_name OR f.home_team = t_home.site_name)
        JOIN teams t_away ON (f.away_team = t_away.api_name OR f.away_team = t_away.site_name)
        JOIN user_favorites uf ON (uf.team_id = t_home.id OR uf.team_id = t_away.id)
        JOIN users u ON (uf.user_id = u.id)
        WHERE f.game_date <= NOW() 
          AND f.processed = FALSE;
    """
    
    try:
        cursor.execute(query)
        alertas_pendentes = cursor.fetchall()
        
        if not alertas_pendentes:
            print("ℹ️ Nenhum alerta personalizado para enviar neste minuto.")
            return

        fixtures_processadas = set()

        for registro in alertas_pendentes:
            fixture_id = registro[0]
            home_team = registro[1]
            away_team = registro[2]
            name_league = registro[3]
            chat_id = registro[4]

            mensagem = (
                f"⚽ <b>Seu time vai entrar em campo!</b>\n\n"
                f"⚔️ <b>{home_team}</b> x <b>{away_team}</b>\n"
                f"🏆 Liga: {name_league}\n"
                f"⏱️ A bola já vai rolar!"
            )

            # Dispara para o Telegram do usuário específico
            sucesso = enviar_alerta_telegram(chat_id, mensagem)
            
            if sucesso:
                fixtures_processadas.add(fixture_id)

        if fixtures_processadas:
            query_update = "UPDATE fixtures SET processed = TRUE WHERE id = %s;"
            for f_id in fixtures_processadas:
                cursor.execute(query_update, (f_id,))
            conn.commit()
            print(f"✅ {len(fixtures_processadas)} jogos foram marcados como processados.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Erro na rotina de envio de alertas: {e}")
    finally:
        cursor.close()
        conn.close()


def rotina_matinal_jogos():
    print("🌅 [08:00] Iniciando rotina matinal de processamento e envio de jogos...")
    
    mensagens_por_time = msg_por_fixture()
    
    if mensagens_por_time:
        disparar_agenda_matinal_usuarios(mensagens_por_time)
        print("✅ Agenda de jogos enviada aos usuários com sucesso!")
    else:
        print("ℹ️ Nenhuma mensagem a ser disparada hoje.")


def verificar_jogos():

    print("🔎 Verificando jogos...")

    jogos = buscar_jogos_do_dia() 

    if not jogos:
        print("ℹ️ Nenhum jogo encontrado para enviar.")
        return

    mensagem = formatar_lista_jogos(jogos)
    enviar_mensagem(mensagem)



def iniciar_scheduler():
    print("🚀 Configurando agendador de tarefas...")

    scheduler.add_job(
        verificar_e_enviar_alertas_proximos_jogos,
        "interval",
        minutes=10,
        timezone="America/Sao_Paulo"
    )

    scheduler.start()
    print("✅ Scheduler em execução!")


def job_03am_carga_api():
    schedule_fixtures()

def job_07am_processar_transmissoes():
    rotina_matinal_jogos()
    pass

# 🛠️ Tarefa 3 (08:00): Cruza os favoritos dos usuários com o mapa e dispara
def job_08am_disparar_telegram():
    usuarios = obter_todos_usuarios_com_favoritos()
    # Executa o loop do SET por usuário e envia via enviar_alerta_telegram()
    pass