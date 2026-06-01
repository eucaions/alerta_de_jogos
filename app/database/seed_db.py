import os
import requests
import psycopg2
from dotenv import load_dotenv
from pathlib import Path


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

if __name__ == "__main__":
    cadastrar_liga_e_times(api_liga_id=72, nome_liga="Brasileirão Série B", pais_liga="Brazil")
    pass