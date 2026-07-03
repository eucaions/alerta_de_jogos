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

        cursor.execute("DROP TABLE IF EXISTS user_favorite CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS team CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS league CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS fixture CASCADE;")


        cursor.execute("""
            CREATE TABLE IF NOT EXISTS country (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
            );
        """)


        cursor.execute("""
            CREATE TABLE IF NOT EXISTS league (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                country_id INTEGER REFERENCES country(id) ON DELETE SET NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                api_id VARCHAR(100) NOT NULL,
                site_name varchar(100),
                country_id INTEGER REFERENCES country(id) ON DELETE SET NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_favorites (
                id SERIAL PRIMARY KEY,
                user_identifier VARCHAR(100) NOT NULL,
                team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
            );
        """)


        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fixtures (
                id SERIAL PRIMARY KEY,
                home_team VARCHAR(100) NOT NULL,
                away_team VARCHAR(100) NOT NULL,
                name_league VARCHAR(100) NOT NULL,
                game_date datatime NOT NULL,
                status VARCHAR(30) NOT NULL,
                precessed BOOLEAN NOT NULL,

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