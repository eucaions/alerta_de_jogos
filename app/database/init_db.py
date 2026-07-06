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
        cursor.execute("DROP TABLE IF EXISTS leagues CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS country CASCADE;")

        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS country (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS league (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                api_id INTEGER NOT NULL UNIQUE,  -- Adicionado UNIQUE para o seed de ligas
                api_name VARCHAR(100) NOT NULL,
                country_id INTEGER REFERENCES country(id) ON DELETE SET NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team (
                id SERIAL PRIMARY KEY,
                api_id INTEGER NOT NULL UNIQUE,
                api_name VARCHAR(100) NOT NULL,
                site_name VARCHAR(100),
                country_id INTEGER REFERENCES country(id) ON DELETE SET NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_favorites (
                id SERIAL PRIMARY KEY,
                user_identifier VARCHAR(100) NOT NULL,
                team_id INTEGER REFERENCES team(id) ON DELETE CASCADE
                -- CORREÇÃO 2: Removida a vírgula que sobrava aqui
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fixture (
                id SERIAL PRIMARY KEY,
                home_team VARCHAR(100) NOT NULL,
                away_team VARCHAR(100) NOT NULL,
                name_league VARCHAR(100) NOT NULL,
                game_date TIMESTAMP NOT NULL,    
                status VARCHAR(30) NOT NULL,
                processed BOOLEAN NOT NULL DEFAULT FALSE, 

                team_id INTEGER REFERENCES team(id) ON DELETE CASCADE,
                league_id INTEGER REFERENCES league(id) ON DELETE CASCADE
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