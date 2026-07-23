import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from app.database.init_db import obter_conexao

load_dotenv()

FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

HEADERS = {
    'x-apisports-key': FOOTBALL_API_KEY 
}


def schedule_fixtures():
    """
    [03:00] Consulta a API-Sports buscando todas as partidas do dia
    e insere os dados na tabela 'fixtures'.
    """
    url = "https://v3.football.api-sports.io/fixtures"
    day = datetime.now()
    
    params = {
        "date": day.strftime("%Y-%m-%d"),
        "timezone": "America/Sao_Paulo"
    }

    conn = None
    cursor = None

    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        
        if response.status_code != 200:
            print(f"⚠️ Erro ao consultar API-Sports: Status {response.status_code}")
            return

        data = response.json()
        fixtures = data.get("response", [])

        if not fixtures:
            print(f"ℹ️ Nenhuma fixture encontrada na API para a data {day.strftime('%Y-%m-%d')}.")
            return

        conn = obter_conexao()
        cursor = conn.cursor()

        query = """
            INSERT INTO fixtures (id_home_api, id_away_api, id_league_api, game_date, game_time, status)
            VALUES (%s, %s, %s, %s, %s, %s);
        """

        jogos_inseridos = 0
        for item in fixtures:
            id_home_api = item["teams"]["home"]["id"]
            id_away_api = item["teams"]["away"]["id"]
            id_league = item["league"]["id"]
            
            # Extrai o horário a partir do ISO date retornado
            game_date_iso = item["fixture"]["date"]
            horario = datetime.fromisoformat(game_date_iso).strftime("%H:%M")
            status_jogo = item["fixture"]["status"]["short"] # Ex: 'NS' (Not Started)

            cursor.execute(query, (
                id_home_api,
                id_away_api,
                id_league,
                day.date(),
                horario,
                status_jogo
            ))
            jogos_inseridos += 1

        # Confirma todas as inserções de uma só vez
        conn.commit()
        print(f"✅ Tabela Fixtures preenchida com {jogos_inseridos} jogos para {day.strftime('%Y-%m-%d')}.")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Erro ao salvar fixtures da API no banco: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()