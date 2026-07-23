from datetime import datetime
import json
import os
import psycopg2
from dotenv import load_dotenv
import requests
from app.database.init_db import obter_conexao

load_dotenv()

def obter_termo_busca_time(id):

    conn = obter_conexao()
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT COALESCE(common_name, name) 
            FROM teams 
            WHERE id = %s;
        """
        cursor.execute(query, (id,))
        resultado = cursor.fetchone()
        
        return resultado[0] if resultado else None
        
    except Exception as e:
        print(f"❌ Erro ao consultar nome na cascata: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def listar_todos_os_times():
    conn = obter_conexao()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, common_name FROM teams ORDER BY name ASC;")
    rows = cursor.fetchall()

    times = []
    for row in rows:
        times.append({
            "id": row[0],
            "name": row[1],
            "common_name": row[2] or ""
        })

    cursor.close()
    conn.close()
    return times


def atualizar_common_name_time(time_id: int, novo_common_name: str):
    conn = obter_conexao()
    cursor = conn.cursor()
    
    valor_nome = novo_common_name.strip() if novo_common_name.strip() else None
    cursor.execute("UPDATE team SET site_name = %s WHERE id = %s;", (valor_nome, time_id))

    conn.commit()
    cursor.close()
    conn.close()




    
def obter_todos_usuarios_com_favoritos():

    conn = obter_conexao()
    cursor = conn.cursor()

    query = """
        SELECT 
            u.id AS user_id,
            u.telegram_chat_id,
            ARRAY_AGG(t.api_id) AS lista_team_api_ids
        FROM users u
        JOIN user_favorites uf ON u.id = uf.user_id
        JOIN teams t ON uf.team_id = t.id
        GROUP BY u.id, u.telegram_chat_id;
    """

    try:
        cursor.execute(query)
        usuarios_com_favoritos = cursor.fetchall()

        return usuarios_com_favoritos

    except Exception as e:
        print(f"❌ Erro ao buscar favoritos dos usuários: {e}")
        return []
        
    finally:
        cursor.close()
        conn.close()





def schedule_fixtures():
    url = "https://v3.football.api-sports.io/fixtures"
    day = datetime.now()
    FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")
    headers = {'x-apisports-key': FOOTBALL_API_KEY}
    params = {
        "date": day.strftime("%Y-%m-%d"),
        "timezone": "America/Sao_Paulo"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        for item in data.get("response", []):
            
            id_home_api = item["teams"]["home"]["id"]
            id_away_api = item["teams"]["away"]["id"]

            id_league = item["league"]["id"]
            
            horario = datetime.fromisoformat(item["fixture"]["date"]).strftime("%H:%M")

            conn = obter_conexao()
            cursor = conn.cursor()

            query = "INSERT INTO fixtures(id_home_api,id_away_api,id_league_api,game_date,game_time,status) VALUES (%s,%s,%s,%s,%s);"
            cursor.execute(query,(id_home_api,id_away_api,id_league,day,horario,None,))
        conn.commit()
        print(f"Tabela Fixtures preenchida para {day.strftime("%Y-%m-%d")}")

    except Exception as e:
            print(f"❌ Erro no Scraping: {e}")
            return "📺 Erro ao processar guia"
    



def registrar_log_admin(cursor, logs):
    """
    Insere os jogos não pareados pelo scraper na tabela de auditoria/admin.
    """
    query = """
        INSERT INTO admin_logs (tipo, detalhes, criado_em)
        VALUES ('SCRAPER_MISS', %s, NOW());
    """
    cursor.execute(query, (json.dumps(logs),))

