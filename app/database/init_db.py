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

def obter_conexao():
    config_conexao = {
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASS"),
        "host": os.getenv("DB_HOST"), 
        "port": os.getenv("DB_PORT")
    }
    return psycopg.connect(**config_conexao)




def create_tables():

    conn = None
    try:
        print("🔌 Conectando ao PostgreSQL no Docker...")
        conn = obter_conexao()
        cursor = conn.cursor()


        cursor.execute("DROP TABLE IF EXISTS user_favorites CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS fixture CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS team CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS league CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS country CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS user_favorites CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS fixtures CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS teams CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS leagues CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS countries CASCADE;")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS countries (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leagues (
                id SERIAL PRIMARY KEY,
                site_name VARCHAR(100),
                id_api INTEGER NOT NULL UNIQUE,
                api_name VARCHAR(100) NOT NULL,
                country_id INTEGER REFERENCES countries(id) ON DELETE SET NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id SERIAL PRIMARY KEY,
                id_api INTEGER NOT NULL UNIQUE,
                api_name VARCHAR(100) NOT NULL,
                site_name VARCHAR(100),
                country_id INTEGER REFERENCES countries(id) ON DELETE SET NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_chat_id VARCHAR(100) NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_favorites (
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
                PRIMARY KEY (user_id, team_id)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fixtures (
                id SERIAL PRIMARY KEY,
                id_home_api VARCHAR(100) NOT NULL,
                id_away_api VARCHAR(100) NOT NULL,
                id_league_api VARCHAR(100) NOT NULL,
                game_date DATE NOT NULL,
                game_time TIME NOT NULL,    
                status VARCHAR(30) NOT NULL,
                processed BOOLEAN NOT NULL DEFAULT FALSE, 

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