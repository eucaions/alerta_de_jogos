import psycopg
import os
from dotenv import load_dotenv
from pathlib import Path
import traceback

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

print(os.getenv("DB_HOST"))
print(os.getenv("DB_PORT"))
print(BASE_DIR / ".env")


def create_tables():
    config_conexao = {
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASS"),
        "host": os.getenv("DB_HOST"), 
        "port": os.getenv("DB_PORT")
    }

    conn = None
    try:
        print("🔌 Conectando ao PostgreSQL no Docker...")
        conn = psycopg.connect(**config_conexao)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leagues (
                id SERIAL PRIMARY KEY,
                api_id INTEGER UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                country VARCHAR(50)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id SERIAL PRIMARY KEY,
                api_id INTEGER UNIQUE NOT NULL,
                full_name_api VARCHAR(150) NOT NULL,
                search_name_scraping VARCHAR(100),
                league_id INTEGER REFERENCES leagues(id) ON DELETE SET NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_favorites (
                id SERIAL PRIMARY KEY,
                user_identifier VARCHAR(100) NOT NULL,
                team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
                league_id INTEGER REFERENCES leagues(id) ON DELETE CASCADE
            );
        """)

        conn.commit()
        print("✨ Estrutura do banco de dados criada com sucesso dentro do Docker!")
        cursor.close()
        
    except Exception as e:
        print(f"❌ Erro ao inicializar o banco de dados:")
        traceback.print_exc()

        if conn:
            conn.rollback()
            
    finally:
        if conn is not None:
            conn.close()
            print("🔒 Conexão finalizada.")

if __name__ == "__main__":
    create_tables()