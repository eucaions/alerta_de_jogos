import os
import psycopg
import logging
import traceback
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

DATABASE_URL = os.getenv("DATABASE_URL")


def obter_conexao():
    """Conecta ao PostgreSQL usando DATABASE_URL (Render/Nuvem) ou variáveis individuais (.env/Docker)."""
    if DATABASE_URL:
        # Prioridade 1: Conexão via URL (Render)
        return psycopg.connect(DATABASE_URL)
    
    # Prioridade 2: Fallback via variáveis individuais (Local/Docker)
    config_conexao = {
        "dbname": os.getenv("DB_NAME", "postgres"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASS", "postgres"),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432")
    }
    return psycopg.connect(**config_conexao)


def create_tables():
    """Cria a estrutura de tabelas no PostgreSQL."""
    conn = None
    try:
        logger.info("🔌 Conectando ao PostgreSQL para criar DDL...")
        conn = obter_conexao()
        cursor = conn.cursor()

        # Limpeza segura se necessário (opcional)
        cursor.execute("DROP TABLE IF EXISTS user_favorites CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS fixtures CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS teams CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS leagues CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS countries CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS users CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS admin_logs CASCADE;")
        
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
                id_home_api INTEGER NOT NULL,
                id_away_api INTEGER NOT NULL,
                id_league_api INTEGER NOT NULL,
                game_date DATE NOT NULL,
                game_time TIME NOT NULL,    
                status VARCHAR(30) NOT NULL,
                processed BOOLEAN NOT NULL DEFAULT FALSE, 

                team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
                league_id INTEGER REFERENCES leagues(id) ON DELETE CASCADE
            );
        """)

        cursor.execute(""" 
            CREATE TABLE IF NOT EXISTS admin_logs (
                id SERIAL PRIMARY KEY,
                tipo VARCHAR(50) NOT NULL,
                detalhes JSONB NOT NULL,
                criado_em TIMESTAMP DEFAULT NOW()
            ); 
        """)

        conn.commit()
        logger.info("✨ Estrutura de tabelas verificada/criada com sucesso no PostgreSQL!")
        cursor.close()
        
    except Exception as e:
        logger.error("❌ Erro ao inicializar o banco de dados:")
        traceback.print_exc()
        if conn:
            conn.rollback()
            
    finally:
        if conn is not None:
            conn.close()
            logger.info("🔒 Conexão com banco encerrada após DDL.")


if __name__ == "__main__":
    create_tables()