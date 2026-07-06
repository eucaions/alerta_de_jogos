import os
import psycopg2
from dotenv import load_dotenv
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