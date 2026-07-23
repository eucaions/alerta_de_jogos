import requests
from datetime import datetime
import os
import json
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from app.database.queries import obter_termo_busca_time
from app.database.init_db import obter_conexao
from app.database.queries import registrar_log_admin
from thefuzz import fuzz
import re
from app.telegram_bot import enviar_mensagem



def buscar_transmissao_site(time_casa, time_fora, horario_previsto):
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

            # 1. Filtro do Horário exato (ex: "19:30")
            if hora_alvo not in texto_lower:
                continue

            # 2. Aplica Fuzzy Matching nos nomes buscados
            score_casa = fuzz.partial_ratio(time_casa.lower(), texto_lower) if time_casa else 0
            score_fora = fuzz.partial_ratio(time_fora.lower(), texto_lower) if time_fora else 0

            # 3. Se deu match no horário e em pelo menos um dos times
            if score_casa >= LIMIAR_SIMILARIDADE or score_fora >= LIMIAR_SIMILARIDADE:
                print(f"✅ MATCH ({score_casa}% / {score_fora}%): {time_casa} x {time_fora} às {hora_alvo}")
                
                # Extrai a estrutura completa do bloco encontrado
                dados_encontrados = extrair_dados_do_bloco(texto_bloco)
                return dados_encontrados

        print(f"⚠️ Jogo {time_casa} x {time_fora} ({hora_alvo}) não encontrado na grade.")
        return None

    except Exception as e:
        print(f"❌ Erro no Scraping: {e}")
        return None


def extrair_dados_do_bloco(texto_bloco):
    """
    Separa e extrai a liga, os times e a transmissão a partir das linhas do bloco do jogo.
    """

    linhas = [l.strip() for l in texto_bloco.split('\n') if l.strip()]
    
    liga_site = None
    time_casa_site = None
    time_fora_site = None
    canais = "Transmissão não informada"

    for i, linha in enumerate(linhas):
        # 1. Extrai a Liga (está na mesma linha do horário 🕒)
        if '🕒' in linha or re.search(r'\b\d{2}:\d{2}\b', linha):
            # Remove o emoji e o horário para isolar o nome da liga
            # Ex: '🕒 19:30 Campeonato Brasileiro Série A' -> 'Campeonato Brasileiro Série A'
            liga_site = re.sub(r'🕒|\b\d{2}:\d{2}\b', '', linha).strip()

        # 2. Extrai os Times (linha que contém o ' x ' ou ' X ')
        elif ' x ' in linha.lower() and not ('📺' in linha):
            partes_times = re.split(r'\s+[xX]\s+', linha)
            if len(partes_times) == 2:
                time_casa_site = partes_times[0].strip()
                time_fora_site = partes_times[1].strip()

        # 3. Extrai a Transmissão (linha que contém o emoji 📺)
        elif '📺' in linha or 'tv' in linha.lower():
            canais = linha.replace('📺', '').strip()

    return {
        "liga_site": liga_site,
        "time_casa_site": time_casa_site,
        "time_fora_site": time_fora_site,
        "canais": canais
    }




def msg_por_fixture():
    conn = obter_conexao()
    cursor = conn.cursor()

    query = """
        SELECT 
            f.id AS fixture_id,
            f.home_team AS home_api_name,
            f.away_team AS away_api_name,
            f.name_league AS api_league_name,
            f.game_date,
            TO_CHAR(f.game_date, 'HH24:MI') AS game_time,
            t1.api_id AS home_api_id,
            t1.site_name AS home_site_name,
            t2.api_id AS away_api_id,
            t2.site_name AS away_site_name
        FROM fixtures f
        JOIN teams t1 ON f.team_id = t1.id -- ou f.id_home_api = t1.api_id
        JOIN teams t2 ON f.team_id_away = t2.id -- ajuste conforme suas FKS de fixtures
        WHERE f.game_date::date = CURRENT_DATE;
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
            time_casa = jogo[7] or jogo[1]
            time_fora = jogo[9] or jogo[2]
            horario = jogo[5]

            # 2. Executa o Scraping
            dados_scrape = buscar_transmissao_site(time_casa, time_fora, horario)

            if dados_scrape:
                transmissao = dados_scrape['canais']
                liga = dados_scrape['liga_site'] or jogo[3]

                # Atualiza site_name do time da casa se ainda for NULL
                if dados_scrape['time_casa_site'] and not jogo[7]:
                    cursor.execute(
                        "UPDATE teams SET site_name = %s WHERE api_id = %s;",
                        (dados_scrape['time_casa_site'], jogo[6])
                    )

                # Atualiza site_name do time de fora se ainda for NULL
                if dados_scrape['time_fora_site'] and not jogo[9]:
                    cursor.execute(
                        "UPDATE teams SET site_name = %s WHERE api_id = %s;",
                        (dados_scrape['time_fora_site'], jogo[8])
                    )

            else:
                # --- PASSO 2.3: NÃO ENCONTRADO NO SITE ---
                transmissao = "📺 Transmissão não informada no guia"
                liga = jogo[3]

                # Guarda no log de admin para checagem posterior no painel
                nao_encontrados_log.append({
                    "fixture_id": jogo[0],
                    "jogo": f"{time_casa} x {time_fora}",
                    "horario": horario
                })

            # 3. Monta a mensagem individual formatada
            msg_formatada = (
                f"🏆 {liga}\n"
                f"🏟 {time_casa} x {time_fora}\n"
                f"🕒 Horário: {horario}\n"
                f"📺 {transmissao}\n"
                f"----------------------------"
            )

            home_id = jogo[6]
            away_id = jogo[8]

            mensagens_por_time[home_id] = msg_formatada
            mensagens_por_time[away_id] = msg_formatada

        if nao_encontrados_log:
            registrar_log_admin(cursor, nao_encontrados_log)

        conn.commit()
        print(f"✅ Mapeamento concluído! {len(mensagens_por_time)} chaves de times geradas no JSON.")
        
        return mensagens_por_time

    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao processar mensagens das fixtures: {e}")
        return {}
    finally:
        cursor.close()
        conn.close()

