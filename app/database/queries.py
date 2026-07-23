import json
from dotenv import load_dotenv
from app.database.init_db import obter_conexao

load_dotenv()

def obter_termo_busca_time(time_id: int):
    """
    Retorna o site_name/common_name se existir, caso contrário recorre ao api_name.
    """
    conn = obter_conexao()
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT COALESCE(site_name, api_name) 
            FROM teams 
            WHERE id = %s;
        """
        cursor.execute(query, (time_id,))
        resultado = cursor.fetchone()
        
        return resultado[0] if resultado else None
        
    except Exception as e:
        print(f"❌ Erro ao consultar nome na cascata: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


def listar_todos_os_times():
    """
    Lista todos os times ordenados para o painel admin ou seleção do usuário.
    """
    conn = obter_conexao()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, api_name, site_name FROM teams ORDER BY api_name ASC;")
        rows = cursor.fetchall()

        times = []
        for row in rows:
            times.append({
                "id": row[0],
                "api_name": row[1],
                "site_name": row[2] or ""
            })
        return times
    except Exception as e:
        print(f"❌ Erro ao listar times: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def atualizar_site_name_time(time_id: int, novo_site_name: str):
    """
    Atualiza o nome personalizado/site_name do time na tabela teams.
    """
    conn = obter_conexao()
    cursor = conn.cursor()
    
    try:
        valor_nome = novo_site_name.strip() if novo_site_name and novo_site_name.strip() else None
        
        cursor.execute("UPDATE teams SET site_name = %s WHERE id = %s;", (valor_nome, time_id))
        conn.commit()
        print(f"✅ site_name do time ID {time_id} atualizado para '{valor_nome}'")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao atualizar site_name do time: {e}")
    finally:
        cursor.close()
        conn.close()


def obter_todos_usuarios_com_favoritos():
    """
    Busca os usuários com seus respetivos times favoritos agrupados via ARRAY_AGG.
    """
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


def registrar_log_admin(cursor, logs):
    """
    Insere os jogos não pareados pelo scraper na tabela de auditoria/admin.
    Observação: Essa função recebe o 'cursor' externo para reaproveitar a transação ativa.
    """
    try:
        query = """
            INSERT INTO admin_logs (tipo, detalhes, criado_em)
            VALUES ('SCRAPER_MISS', %s, NOW());
        """
        cursor.execute(query, (json.dumps(logs),))
    except Exception as e:
        print(f"❌ Erro ao gravar log do admin: {e}")