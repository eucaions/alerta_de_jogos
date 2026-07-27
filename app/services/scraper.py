import re
import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz
from app.database.init_db import obter_conexao
from app.database.queries import registrar_log_admin


def extrair_dados_do_bloco(p_tag):
    """
    Extrai a liga, os times e os canais de transmissão
    diretamente do objeto Tag BeautifulSoup do parágrafo <p>.
    """
    # Se recebeu o texto cru em vez do objeto Tag, converte
    if isinstance(p_tag, str):
        p_tag = BeautifulSoup(p_tag, 'html.parser')

    # Pega todos os fragmentos de texto limpos do parágrafo
    textos = [t.strip() for t in p_tag.stripped_strings if t.strip()]

    liga_site = None
    time_casa_site = None
    time_fora_site = None
    canais = "Transmissão não informada"

    # Itera sobre os fragmentos de texto do <p>
    for i, texto in enumerate(textos):
        # 1. Identifica a Liga (contém horário, ex: "18:30 Campeonato Brasileiro Série A")
        if re.search(r'\b\d{2}:\d{2}\b', texto):
            liga_site = re.sub(r'\b\d{2}:\d{2}\b', '', texto).strip()

        # 2. Identifica os Times (contém " x " ou " X ")
        elif ' x ' in texto.lower():
            partes = re.split(r'\s+[xX]\s+', texto)
            if len(partes) == 2:
                time_casa_site = partes[0].strip()
                time_fora_site = partes[1].strip()

        # 3. O que sobrou após os times costuma ser o canal (ex: "PREMIERE", "SPORTV")
        # Ignora se for o horário/liga ou os times
        elif not re.search(r'\b\d{2}:\d{2}\b', texto) and not (' x ' in texto.lower()):
            # Se não for o caractere do emoji ou aspas soltas
            texto_limpo = texto.replace('"', '').replace("'", "").strip()
            if texto_limpo and texto_limpo != '📺':
                canais = texto_limpo

    return {
        "liga_site": liga_site,
        "time_casa_site": time_casa_site,
        "time_fora_site": time_fora_site,
        "canais": canais
    }


def buscar_transmissao_site(time_casa, time_fora, horario_previsto):
    url = "https://doentesporfutebol.com.br/guiadejogos/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        paragrafos = soup.find_all('p')
        
        LIMIAR_SIMILARIDADE = 80
        hora_alvo = str(horario_previsto).strip()

        for p in paragrafos:
            texto_bloco = p.get_text().strip()
            texto_lower = texto_bloco.lower()

            # Filtra pelo horário no parágrafo
            if hora_alvo not in texto_lower:
                continue

            score_casa = fuzz.partial_ratio(time_casa.lower(), texto_lower) if time_casa else 0
            score_fora = fuzz.partial_ratio(time_fora.lower(), texto_lower) if time_fora else 0

            if score_casa >= LIMIAR_SIMILARIDADE or score_fora >= LIMIAR_SIMILARIDADE:
                print(f"✅ MATCH ({score_casa}% / {score_fora}%): {time_casa} x {time_fora} às {hora_alvo}")
                # PASSA A TAG <P> DIRETAMENTE AQUI:
                return extrair_dados_do_bloco(p)

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
            t1.id_api AS home_api_id,        
            t1.site_name AS home_site_name,
            t2.id_api AS away_api_id,        
            t2.site_name AS away_site_name,
            l.api_name AS league_api_name,
            l.site_name AS league_site_name
        FROM fixtures f
        JOIN teams t1 ON f.id_home_api::integer = t1.id_api
        JOIN teams t2 ON f.id_away_api::integer = t2.id_api
        LEFT JOIN leagues l ON f.id_league_api::integer = l.id_api
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
            horario_raw = jogo[5]
            if hasattr(horario_raw, 'strftime'):
                horario = horario_raw.strftime("%H:%M")
            else:
                horario = str(horario_raw)[:5]

            home_api_id = jogo[6]
            home_site_name = jogo[7]
            away_api_id = jogo[8]
            away_site_name = jogo[9]
            league_api_name = jogo[10]
            league_site_name = jogo[11]


            # Fallback inteligente: Pega site_name se existir, senão usa api_name
            time_casa = home_site_name or home_api_name
            time_fora = away_site_name or away_api_name

            # 2. Executa o Scraping
            dados_scrape = buscar_transmissao_site(time_casa, time_fora, horario)

            if dados_scrape:
                transmissao = dados_scrape['canais']
                liga = dados_scrape['liga_site'] or league_site_name or league_api_name or "Futebol Profissional"

                # Atualiza site_name do time da casa se ainda estiver NULL no banco
                if dados_scrape['time_casa_site'] and not home_site_name:
                    cursor.execute(
                        "UPDATE teams SET site_name = %s WHERE id_api = %s;",
                        (dados_scrape['time_casa_site'], home_api_id)
                    )

                # Atualiza site_name do time de fora
                if dados_scrape['time_fora_site'] and not away_site_name:
                    cursor.execute(
                        "UPDATE teams SET site_name = %s WHERE id_api = %s;",
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