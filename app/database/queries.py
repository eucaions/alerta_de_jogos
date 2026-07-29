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
    conn = obter_conexao()
    cursor = conn.cursor()

    query = """
        SELECT 
            u.id AS user_id,
            u.telegram_chat_id,
            ARRAY_AGG(t.id_api) AS lista_team_api_ids
        FROM users u
        JOIN user_favorites uf ON u.id = uf.user_id
        JOIN teams t ON uf.team_id = t.id
        GROUP BY u.id, u.telegram_chat_id;
    """
    try:
        cursor.execute(query)
        return cursor.fetchall()
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


def salvar_favoritos_usuario(user_id: int, team_ids: list[int]):
    """
    Atualiza os times favoritos de um usuário.
    Remove os favoritos antigos e insere os novos recebidos da view.
    """
    conn = obter_conexao()
    cursor = conn.cursor()

    try:
        # 1. Remove os favoritos antigos do usuário
        cursor.execute("DELETE FROM user_favorites WHERE user_id = %s;", (user_id,))

        # 2. Insere a nova lista de times favoritos
        if team_ids:
            query_insert = "INSERT INTO user_favorites (user_id, team_id) VALUES (%s, %s);"
            parametros = [(user_id, t_id) for t_id in team_ids]
            cursor.executemany(query_insert, parametros)

        conn.commit()
        print(f"✅ Favoritos atualizados com sucesso para o usuário ID {user_id}!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao salvar favoritos do usuário: {e}")
        return False

    finally:
        cursor.close()
        conn.close()


def obter_favoritos_ids_usuario(user_id: int) -> list[int]:
    """
    Retorna a lista de IDs dos times que o usuário já favoritou (para vir pré-marcado na tela).
    """
    conn = obter_conexao()
    cursor = conn.cursor()

    try:
        query = "SELECT team_id FROM user_favorites WHERE user_id = %s;"
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    except Exception as e:
        print(f"❌ Erro ao buscar favoritos: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def obter_ou_criar_usuario_por_telegram(telegram_chat_id: str) -> int:
    """
    Busca o ID interno do usuário pelo telegram_chat_id.
    Se não existir, cria o registro e devolve o id gerado.
    """
    conn = obter_conexao()
    cursor = conn.cursor()

    try:
        # 1. Tenta buscar o usuário existente
        cursor.execute("SELECT id FROM users WHERE telegram_chat_id = %s;", (telegram_chat_id,))
        row = cursor.fetchone()

        if row:
            return row[0]

        # 2. Se não existir, insere um novo registro de usuário
        cursor.execute(
            "INSERT INTO users (telegram_chat_id) VALUES (%s) RETURNING id;", 
            (telegram_chat_id,)
        )
        novo_id = cursor.fetchone()[0]
        conn.commit()
        print(f"👤 Novo usuário criado no banco com Chat ID: {telegram_chat_id}")
        return novo_id

    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao obter/criar usuário por Telegram ID: {e}")
        return None
    finally:
        cursor.close()
        conn.close()