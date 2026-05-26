import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def obter_termo_busca_time(api_fixture_id):

    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )
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