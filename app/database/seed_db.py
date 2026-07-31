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
    """Conecta ao PostgreSQL aceitando DATABASE_URL (Render) ou variáveis locais (Docker)."""
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
        logger.error("❌ Variável FOOTBALL_API_KEY não foi encontrada no ambiente!")
        return

    # Envia ambos para funcionar tanto com chave direta (API-Sports) quanto via RapidAPI
    headers = {
        "x-apisports-key": FOOTBALL_API_KEY.strip(),
        "x-rapidapi-key": FOOTBALL_API_KEY.strip(),
    }
    
    try:
        for id in ligas:
            logger.info(f"🔍 [SEED] Consultando Liga ID {id}...")
            url_api_league = f"https://v3.football.api-sports.io/leagues?id={id}"
            response = requests.get(url_api_league, headers=headers).json()
            
            # Se a API retornar mensagem de erro/cota, loga aqui
            if response.get('errors'):
                logger.error(f"❌ Erro/Aviso retornado pela API para Liga {id}: {response.get('errors')}")

            lista_liga = response.get('response', [])

            if not lista_liga:
                logger.warning(f"⚠️ Nenhuma liga encontrada para o ID {id}, pulando...")
                continue

            dados_liga = lista_liga[0]
            nome_liga = dados_liga['league']['name']
            nome_pais = dados_liga['country']['name']

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

            query_insert = """
                INSERT INTO leagues (site_name, id_api, api_name, country_id) 
                VALUES (%s, %s, %s, %s) 
                ON CONFLICT (id_api) DO NOTHING;
            """
            cursor.execute(query_insert, (None, id, nome_liga, country_id))
            conn.commit()
            logger.info(f"✅ Liga '{nome_liga}' (ID {id}) gravada no banco.")

            # Mantida a busca na temporada 2024 para o plano gratuito
            url_api_teams = f"https://v3.football.api-sports.io/teams?league={id}&season=2024"
            response_teams = requests.get(url_api_teams, headers=headers).json()
            lista_times = response_teams.get('response', [])
            
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
                        res2 = cursor.fetchone()
                        team_country_id = res2[0] if res2 else None
                else:
                    team_country_id = result2[0]

                logger.info(f"   ↳ Salvando time: ID {api_team_id} - {nome_time_api}")
                
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


def futPythonSeederTeams(conn, country, league, season, league_id=None, international=False):
    FUT_PYTHON_KEY = os.getenv("FUT_PYTHON_KEY")
    url = f"https://futpythontrader.com.br/api/download/{country}/{league}/{season}?api_key={FUT_PYTHON_KEY}"
    
    try:
        df_fut = pd.read_csv(url)
        teams = pd.concat([
            df_fut["Home"].astype(str).str.strip().str.lower(),
            df_fut["Away"].astype(str).str.strip().str.lower()
        ]).unique().tolist()
    except Exception as e:
        logger.warning(f"⚠️ Erro ao baixar ou processar times da liga {league} ({season}): {e}")
        return

    cursor = conn.cursor()
    
    if international:
        teams = [re.sub(r'\s*\([^)]*\)', '', item) for item in teams]

    dados_teams = [(team_name, league_id, None) for team_name in teams]
    
    query = """
        INSERT INTO teams (name, league_id, common_name) 
        VALUES (%s, %s, %s) 
        ON CONFLICT (name) 
        DO UPDATE SET 
            league_id = CASE 
                WHEN EXCLUDED.league_id IS NOT NULL THEN EXCLUDED.league_id 
                ELSE teams.league_id 
            END;
    """
    
    execute_batch(cursor, query, dados_teams)
    conn.commit() 
    cursor.close()
    logger.info(f"⚽ {len(teams)} times processados para a liga: {league}")


def rodar_seeder():
    grupos_de_ligas = [
        [2, 3, 11, 13, 39],
        [40, 61, 71, 72, 78],
        [94, 135, 140, 848, 866]
    ]
    INTERVALO_SEGUNDOS = 60

    for indice, ligas in enumerate(grupos_de_ligas):
        logger.info(f"🚀 Iniciando o lote {indice + 1}/{len(grupos_de_ligas)}: Ligas {ligas}")
        
        oficialSeed(ligas)
        
        if indice < len(grupos_de_ligas) - 1:
            logger.info(f"⏳ Lote {indice + 1} finalizado. Aguardando {INTERVALO_SEGUNDOS} segundos para o próximo lote...")
            time.sleep(INTERVALO_SEGUNDOS)

    logger.info("✨ Todos os lotes de seed foram executados com sucesso!")


if __name__ == "__main__":
    rodar_seeder()