import os
import psycopg2
from dotenv import load_dotenv
from app.database.init_db import obter_conexao

load_dotenv()

def obter_termo_busca_time(api_fixture_id):

    conn = obter_conexao()
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT COALESCE(common_name, fullname_api_database, fullname_api_fixture) 
            FROM teams 
            WHERE api_fixture_id = %s;
        """
        cursor.execute(query, (api_fixture_id,))
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

    cursor.execute("SELECT id, fullname_api_fixture, common_name FROM teams ORDER BY fullname_api_fixture ASC;")
    rows = cursor.fetchall()

    times = []
    for row in rows:
        times.append({
            "id": row[0],
            "api_name": row[1],
            "common_name": row[2] or ""
        })

    cursor.close()
    conn.close()
    return times


def atualizar_common_name_time(time_id: int, novo_common_name: str):
    conn = obter_conexao()
    cursor = conn.cursor()
    
    valor_nome = novo_common_name.strip() if novo_common_name.strip() else None
    cursor.execute("UPDATE teams SET common_name = %s WHERE id = %s;", (valor_nome, time_id))

    conn.commit()
    cursor.close()
    conn.close()