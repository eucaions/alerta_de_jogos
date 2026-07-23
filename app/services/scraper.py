import re
import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz
from app.database.init_db import obter_conexao
from app.database.queries import registrar_log_admin


def extrair_dados_do_bloco(texto_bloco):
    """
    Separa e extrai a liga, os times e a transmissão a partir das linhas do bloco do jogo.
    """
    linhas = [l.strip() for l in texto_bloco.split('\n') if l.strip()]
    
    liga_site = None
    time_casa_site = None
    time_fora_site = None
    canais = "Transmissão não informada"

    for linha in linhas:
        # 1. Extrai a Liga (linha contendo horário ou o emoji 🕒)
        if '🕒' in linha or re.search(r'\b\d{2}:\d{2}\b', linha):
            liga_site = re.sub(r'🕒|\b\d{2}:\d{2}\b', '', linha).strip()

        # 2. Extrai os Times (linha contendo ' x ' ou ' X ')
        elif ' x ' in linha.lower() and not ('📺' in linha):
            partes_times = re.split(r'\s+[xX]\s+', linha)
            if len(partes_times) == 2:
                time_casa_site = partes_times[0].strip()
                time_fora_site = partes_times[1].strip()

        # 3. Extrai a Transmissão (linha contendo '📺' ou termos de TV)
        elif '📺' in linha or 'tv' in linha.lower():
            canais = linha.replace('📺', '').strip()

    return {
        "liga_site": liga_site,
        "time_casa_site": time_casa_site,
        "time_fora_site": time_fora_site,
        "canais": canais
    }


def buscar_transmissao_site(time_casa, time_fora, horario_previsto):
    """
    Realiza o scraping no site e aplica Fuzzy Matching para localizar a partida e sua transmissão.
    """
    url = "https://doentesporfutebol.com.br/guiadejogos/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        paragrafos = soup.find_all('p')
        
        LIMIAR_SIMILARIDADE = 80
        hora_alvo = horario_previsto.strip()

        for p in paragrafos:
            texto_bloco = p.get_text(separator="\n").strip()
            texto_lower = texto_bloco.lower()

            # 1. Filtro pelo Horário
            if hora_alvo not in texto_lower:
                continue

            # 2. Fuzzy Matching nos nomes dos times
            score_casa = fuzz.partial_ratio(time_casa.lower(), texto_lower) if time_casa else 0
            score_fora = fuzz.partial_ratio(time_fora.lower(), texto_lower) if time_fora else 0

            # 3. Match confirmado no horário + pelo menos um dos times
            if score_casa >= LIMIAR_SIMILARIDADE or score_fora >= LIMIAR_SIMILARIDADE:
                print(f"✅ MATCH ({score_casa}% / {score_fora}%): {time_casa} x {time_fora} às {hora_alvo}")
                return extrair_dados_do_bloco(texto_bloco)

        print(f"⚠️ Jogo {time_casa} x {time_fora} ({hora_alvo}) não encontrado na grade do site.")
        return None

    except Exception as e:
        print(f"❌ Erro no Scraping: {e}")
        return None


def msg_por_fixture():
    """
    Cruza as fixtures do dia no banco com o scraper, atualiza site_names,
    gera os logs do admin e retorna o dicionário.
    """
    conn = obter_conexao()
    cursor = conn.cursor()

    query = """
        SELECT 
            f.id AS fixture_id,
            t1.api_name AS home_api_name,
            t2.api_name AS away_api_name,
            f.id_league_api AS api_league,
            f.game_date,
            f.game_time,
            t1.api_id AS home_api_id,
            t1.site_name AS home_site_name,
            t2.api_id AS away_api_id,
            t2.site_name AS away_site_name
        FROM fixtures f
        JOIN teams t1 ON f.id_home_api = t1.api_id
        JOIN teams t2 ON f.id_away_api = t2.api_id
        WHERE f.game_date = CURRENT_DATE;
    """
    
    try:
        cursor.execute(query)
        jogos_do_dia = cursor.fetchall()

        if not jogos_do_dia:
            print("ℹ️ Nenhum jogo encontrado na tabela fixtures para o dia de hoje.")
            return {}

        mensagens_por_time = {}
        nao_encontrados_log = []

        for jogo in jogos_do_dia:
            fixture_id = jogo[0]
            home_api_name = jogo[1]
            away_api_name = jogo[2]
            horario = jogo[5]
            home_api_id = jogo[6]
            home_site_name = jogo[7]
            away_api_id = jogo[8]
            away_site_name = jogo[9]

            # Fallback inteligente: Pega site_name se existir, senão usa api_name
            time_casa = home_site_name or home_api_name
            time_fora = away_site_name or away_api_name

            # 2. Executa o Scraping
            dados_scrape = buscar_transmissao_site(time_casa, time_fora, horario)

            if dados_scrape:
                transmissao = dados_scrape['canais']
                liga = dados_scrape['liga_site'] or "Futebol Profissional"

                # Atualiza site_name do time da casa se ainda estiver NULL no banco
                if dados_scrape['time_casa_site'] and not home_site_name:
                    cursor.execute(
                        "UPDATE teams SET site_name = %s WHERE api_id = %s;",
                        (dados_scrape['time_casa_site'], home_api_id)
                    )

                # Atualiza site_name do time de fora se ainda estiver NULL no banco
                if dados_scrape['time_fora_site'] and not away_site_name:
                    cursor.execute(
                        "UPDATE teams SET site_name = %s WHERE api_id = %s;",
                        (dados_scrape['time_fora_site'], away_api_id)
                    )

            else:
                # Caso o jogo não tenha sido pareado pelo scraper
                transmissao = "📺 Transmissão não informada no guia"
                liga = "Futebol Profissional"

                nao_encontrados_log.append({
                    "fixture_id": fixture_id,
                    "jogo": f"{time_casa} x {time_fora}",
                    "horario": horario
                })

            # 3. Monta a mensagem formatada para o Telegram
            msg_formatada = (
                f"🏆 {liga}\n"
                f"🏟 {time_casa} x {time_fora}\n"
                f"🕒 Horário: {horario}\n"
                f"📺 {transmissao}\n"
                f"----------------------------"
            )

            # Mapeia a mesma mensagem para ambos os times
            mensagens_por_time[home_api_id] = msg_formatada
            mensagens_por_time[away_api_id] = msg_formatada

        # Grava os não pareados na tabela de logs de administração
        if nao_encontrados_log:
            registrar_log_admin(cursor, nao_encontrados_log)

        conn.commit()
        print(f"✅ Mapeamento concluído! {len(mensagens_por_time)} chaves de times geradas.")
        
        return mensagens_por_time

    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao processar mensagens das fixtures: {e}")
        return {}
        
    finally:
        cursor.close()
        conn.close()