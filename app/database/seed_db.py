import os
import requests
import psycopg2
import json
import re
import time
import logging
import traceback
from dotenv import load_dotenv
from pathlib import Path
import pandas as pd
from psycopg2.extras import execute_batch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=True)


def conectar_banco():
    """Conecta ao banco usando DATABASE_URL (Render) ou variáveis individuais (Docker/Local)."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)
    
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS", "postgres"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432")
    )


def oficialSeed(ligas=[]):
    conn = conectar_banco()
    cursor = conn.cursor()
    FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")
    
    if not FOOTBALL_API_KEY:
        logger.error("❌ FOOTBALL_API_KEY não configurada no .env / Render!")
        return

    headers = {
        "x-rapidapi-key": FOOTBALL_API_KEY,
    }
    
    # Define o ano atual dinamicamente para a busca da temporada
    SEASON_ATUAL = os.getenv("FOOTBALL_SEASON", "2024")

    try:
        for liga_id in ligas:
            logger.info(f"🔍 [SEED] Buscando dados da liga ID: {liga_id}...")
            url_api_league = f"https://v3.football.api-sports.io/leagues?id={liga_id}"
            response = requests.get(url_api_league, headers=headers).json()
            lista_liga = response.get('response', [])

            if not lista_liga:
                logger.warning(f"⚠️ Nenhuma liga encontrada para o ID {liga_id}, pulando...")
                continue

            dados_liga = lista_liga[0]
            nome_liga = dados_liga['league']['name']
            nome_pais = dados_liga['country']['name']

            # 1. Trata País da Liga
            query_busca = "SELECT c.id FROM countries AS c WHERE c.name = (%s);"
            cursor.execute(query_busca, (nome_pais,))
            result = cursor.fetchone()

            if not result:
                query_new_country = "INSERT INTO countries (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id;"
                cursor.execute(query_new_country, (nome_pais,))
                insert_result = cursor.fetchone()
                
                if insert_result:
                    country_id = insert_result[0]
                else:
                    cursor.execute(query_busca, (nome_pais,))
                    res = cursor.fetchone()
                    country_id = res[0] if res else None
                conn.commit()
            else:
                country_id = result[0]

            # 2. Insere a Liga
            query_insert = """
                INSERT INTO leagues (site_name, id_api, api_name, country_id) 
                VALUES (%s, %s, %s, %s) 
                ON CONFLICT (id_api) DO NOTHING;
            """
            cursor.execute(query_insert, (None, liga_id, nome_liga, country_id))
            conn.commit()
            logger.info(f"✅ Liga '{nome_liga}' gravada no banco.")

            # 3. Busca Times da Liga
            url_api_teams = f"https://v3.football.api-sports.io/teams?league={liga_id}&season={SEASON_ATUAL}"
            response_teams = requests.get(url_api_teams, headers=headers).json()
            lista_times = response_teams.get('response', [])

            if not lista_times:
                logger.warning(f"⚠️ Nenhum time encontrado para a liga {nome_liga} na temporada {SEASON_ATUAL}.")
                continue

            for item in lista_times:
                team_data = item.get('team')
                if not team_data:
                    continue
                    
                api_team_id = team_data.get('id')
                nome_time_api = team_data.get('name')
                country_name_team = team_data.get('country')
                
                cursor.execute(query_busca, (country_name_team,))
                result2 = cursor.fetchone()

                if not result2:
                    query_new_country = "INSERT INTO countries (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id;"
                    cursor.execute(query_new_country, (country_name_team,))
                    insert_result = cursor.fetchone()
                    if insert_result:
                        team_country_id = insert_result[0]
                    else:
                        cursor.execute(query_busca, (country_name_team,))
                        res = cursor.fetchone()
                        team_country_id = res[0] if res else None
                else:
                    team_country_id = result2[0]

                logger.info(f"   ↳ Salvando Time: ID {api_team_id} - {nome_time_api}")
                
                cursor.execute("""
                    INSERT INTO teams (id_api, api_name, country_id, site_name)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (id_api) DO NOTHING;
                """, (api_team_id, nome_time_api, team_country_id, None))
                                
            conn.commit()

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Erro fatal durante o seed: {e}")
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()


def rodar_seeder_completo():
    """Função executável que gerencia a rotina de lotes com timers."""
    grupos_de_ligas = [
        [2, 3, 11, 13, 39],      # Champions, Europa League, etc.
        [40, 61, 71, 72, 78],    # Brasileirão Série A, Série B, etc.
        [94, 135, 140, 848, 866]
    ]
    INTERVALO_SEGUNDOS = 15  # Reduzido de 60s para dinamizar o seed em lote

    for indice, ligas in enumerate(grupos_de_ligas):
        logger.info(f"🚀 Iniciando Lote {indice + 1}/{len(grupos_de_ligas)}: Ligas {ligas}")
        oficialSeed(ligas)
        
        if indice < len(grupos_de_ligas) - 1:
            logger.info(f"⏳ Aguardando {INTERVALO_SEGUNDOS}s para o próximo lote (Respeitando Rate Limit)...")
            time.sleep(INTERVALO_SEGUNDOS)

    logger.info("✨ Todos os lotes de seed foram executados com sucesso!")


if __name__ == "__main__":
    rodar_seeder_completo()