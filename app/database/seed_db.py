import os
import requests
import psycopg2
import json
import re
import time

from dotenv import load_dotenv
from pathlib import Path
import pandas as pd
from psycopg2.extras import execute_batch


BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=True)


def conectar_banco():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT") 
    )

def cadastrar_liga_e_times(api_liga_id, nome_liga, pais_liga):
    conn = conectar_banco()
    FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

    cursor = conn.cursor()
    
    try:
        # 1. Insere a Liga no Banco
        cursor.execute("""
            INSERT INTO leagues (api_id, name, country)
            VALUES (%s, %s, %s)
            ON CONFLICT (api_id) DO UPDATE SET name = EXCLUDED.name
            RETURNING id;
        """, (api_liga_id, nome_liga, pais_liga))
        
        id_liga_no_banco = cursor.fetchone()[0]
        print(f"🔹 Liga registrada no banco com ID interno: {id_liga_no_banco}")
        
        url_api = f"https://v3.football.api-sports.io/teams?league={api_liga_id}&season=2024"
        headers = {
            "x-rapidapi-key": FOOTBALL_API_KEY, 
        } 
        
        print(f"📡 Chamando API: {url_api}")
        response = requests.get(url_api, headers=headers).json()
        
        # --- PRINT DE SEGURANÇA 1 ---
        # Vamos ver o que a API respondeu de verdade
        print(f"🔍 Status da API: {response.get('errors') if response.get('errors') else 'Sem erros aparentes'}")
        lista_times = response.get('response', [])
        print(f"📊 Quantidade de times retornados pela API: {len(lista_times)}")
        # ----------------------------

        contador_inseridos = 0
        
        # 3. Loop de Inserção
        for item in lista_times:
            team_data = item.get('team')
            if not team_data:
                print("⚠️ Estrutura do JSON inválida para este item, pulando...")
                continue
                
            api_team_id = team_data.get('id')
            nome_time_api = team_data.get('name')
            
            # --- PRINT DE SEGURANÇA 2 ---
            print(f"   ↳ Tentando salvar: ID {api_team_id} - {nome_time_api}")
            
            cursor.execute("""
                INSERT INTO teams (api_fixture_id, fullname_api_fixture, league_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (api_fixture_id) DO NOTHING;
            """, (api_team_id, nome_time_api, id_liga_no_banco))
            
            contador_inseridos += 1
            
        conn.commit()
        print(f"✨ Transação concluída! Total de comandos INSERT executados: {contador_inseridos}")
        
    except Exception as e:
        print(f"❌ Erro ao popular banco: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()








def oficialSeed(ligas = []):
    conn = conectar_banco()
    FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

    cursor = conn.cursor()

    with open("countries.json", "r") as f:
        countries_json = json.load(f)

    countries = []
    for i in countries_json:
        vet = [i['name']]
        countries.append(vet)

    headers = {
        "x-rapidapi-key": FOOTBALL_API_KEY, 
    } 
    try:
        query_country = "INSERT INTO countries (name) VALUES (%s) ON CONFLICT DO NOTHING;"
        execute_batch(cursor,query_country,countries)
        conn.commit()


        for id in ligas:
            url_api_league = f"https://v3.football.api-sports.io/leagues?id={id}"
            response = requests.get(url_api_league, headers=headers).json()
            lista_liga = response.get('response', [])

            if not lista_liga:
                print(f"⚠️ Nenhuma liga encontrada para o ID {id}, pulando...")
                continue

            dados_liga = lista_liga[0]
            nome_liga = dados_liga['league']['name']
            nome_pais = dados_liga['country']['name']

            query_busca = "SELECT c.id FROM countries AS c WHERE c.name = (%s);"
            cursor.execute(query_busca, (nome_pais,))
            result = cursor.fetchone()

            if not result:
                # CORREÇÃO 1 & 2: Passamos 'nome_pais' e usamos RETURNING id para capturar o ID gerado na hora
                query_new_country = "INSERT INTO countries (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id;"
                cursor.execute(query_new_country, (nome_pais,))
                
                insert_result = cursor.fetchone()
                
                if insert_result:
                    country_id = insert_result[0]
                else:
                    cursor.execute(query_busca, (nome_pais,))
                    country_id = cursor.fetchone()[0]
                    
                conn.commit()
            else:
                country_id = result[0]

            query_insert = """
                INSERT INTO leagues (name, api_id, api_name, country_id) 
                VALUES (%s, %s, %s, %s) 
                ON CONFLICT (api_id) DO NOTHING;
            """
            cursor.execute(query_insert, (None, id, nome_liga, country_id))


            url_api_teams = f"https://v3.football.api-sports.io/teams?league={id}&season=2024"
            response = requests.get(url_api_teams, headers=headers).json()
            lista_times = response.get('response', [])
            for item in lista_times:
                team_data = item.get('team')
                if not team_data:
                    continue
                    
                api_team_id = team_data.get('id')
                nome_time_api = team_data.get('name')
                
                print(f"   ↳ Tentando salvar: ID {api_team_id} - {nome_time_api}")
                
                cursor.execute("""
                    INSERT INTO teams (api_id, api_name, country_id, site_name)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (api_id) DO NOTHING;
                """, (api_team_id, nome_time_api, country_id, None))
                                
            conn.commit()

    except Exception as e:
            conn.rollback()
            print(f"❌ Erro fatal durante o seed: {e}")
    finally:
        cursor.close()
        conn.close()
















def futPythonSeederTeams(conn, country, league, season, league_id=None, international = False):
    FUT_PYTHON_KEY = os.getenv("FUT_PYTHON_KEY")
    url = f"https://futpythontrader.com.br/api/download/{country}/{league}/{season}?api_key={FUT_PYTHON_KEY}"
    
    try:
        df_fut = pd.read_csv(url)
        teams = pd.concat([
            df_fut["Home"].astype(str).str.strip().str.lower(),
            df_fut["Away"].astype(str).str.strip().str.lower()
        ]).unique().tolist()
    except Exception as e:
        print(f"⚠️ Erro ao baixar ou processar times da liga {league} ({season}): {e}")
        return

    cursor = conn.cursor()
    
    if(international):
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
    print(f"⚽ {len(teams)} times processados para a liga: {league}")


def seeding_teams_and_leagues():
    # 1. Carrega todos os arquivos JSON
    with open("national_leagues_full_year.json", "r") as f:
        nat_fy = json.load(f)
    with open("national_leagues_half_year.json", "r") as f:
        nat_hy = json.load(f)
    with open("international_leagues_full_year.json", "r") as f:
        inter_fy = json.load(f)
    with open("international_leagues_half_year.json", "r") as f:
        inter_hy = json.load(f)

    todas_ligas = []
    todas_ligas.extend(nat_fy)
    todas_ligas.extend(nat_hy)
    todas_ligas.extend(inter_fy)
    todas_ligas.extend(inter_hy)


    ligas_unicas = {(item["league"], item["country"]) for item in todas_ligas}
    data_db = list(ligas_unicas)

    conn = conectar_banco()
    cursor = conn.cursor()

    print("Iniciando seed de ligas...")
    query_leagues = "INSERT INTO leagues (name, country) VALUES (%s, %s) ON CONFLICT DO NOTHING;"
    execute_batch(cursor, query_leagues, data_db)
    conn.commit()


    grupos_temporadas = [
        (nat_fy, "2026", True),         
        (nat_hy, "2025-2026", True),    
        (inter_fy, "2026", False),
        (inter_hy, "2025-2026", False)
    ]

    for lista_json, season, is_national in grupos_temporadas:
        for item in lista_json:
            league = item["league"]
            country = item["country"]

            league_id = None  

            if is_national:
                cursor.execute("SELECT id FROM leagues WHERE name = %s;", (league,))
                result = cursor.fetchone()
                if result:
                    league_id = result[0]
            else:
                pass

            if(is_national):
                print(f"Buscando times para: {league} (Nacional) | Temporada: {season}...")
                futPythonSeederTeams(conn, country=country, league=league, season=season, league_id=league_id)

            else:
                print(f"Buscando times para: {league} (Internacional) | Temporada: {season}...")
                futPythonSeederTeams(conn, country=country, league=league, season=season, league_id=league_id, international=True)


            

    cursor.close()
    conn.close()
    print("Sucesso")

if __name__ == "__main__":
    """ cadastrar_liga_e_times(api_liga_id=72, nome_liga="Brasileirão Série B", pais_liga="Brazil") """
    """ futPythonSeederTeams("brazil", "serie-b", "2026") """

    # limite de 5, pois o site nao permite mais

    grupos_de_ligas = [
        [2, 3, 11, 13, 39],
        [40, 61, 71, 72, 78],
        [94, 135 ,140, 848, 866]
    ]
    INTERVALO_SEGUNDOS = 60

    for indice, ligas in enumerate(grupos_de_ligas):
        print(f"🚀 Iniciando o lote {indice + 1}/{len(grupos_de_ligas)}: Ligas {ligas}")
        
        # Executa a função que criamos para o lote atual
        oficialSeed(ligas)
        
        # Se ainda não for o último lote, aplica o timer antes do próximo disparo
        if indice < len(grupos_de_ligas) - 1:
            print(f"⏳ Lote {indice + 1} finalizado. Aguardando {INTERVALO_SEGUNDOS} segundos para o próximo lote...")
            time.sleep(INTERVALO_SEGUNDOS)

    print("✨ Todos os lotes de seed foram executados com sucesso!")


    pass