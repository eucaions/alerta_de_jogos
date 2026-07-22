import requests
from datetime import datetime
import os
import json
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from app.database.queries import obter_termo_busca_time
from app.database.init_db import obter_conexao
from thefuzz import fuzz
import re

load_dotenv()

FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

HEADERS = {
    'x-apisports-key': FOOTBALL_API_KEY 
}

    
def extrair_canais_mapeados(texto_bruto: str) -> str:
    if not texto_bruto:
        return "📺 Consultar guias"

    MAPEAMENTO = {
        "globo": "Globo",
        "sportv": "SporTV",
        "premiere": "Premiere",
        "espn": "ESPN",
        "espn 2": "ESPN",
        "espn 3": "ESPN",
        "espn 4": "ESPN",
        "espn2": "ESPN",
        "espn3": "ESPN",
        "espn4": "ESPN",   
        "tnt" : "TNT",
        "disney": "Disney+",
        "disney+": "Disney+",
        "disney+ premium": "Disney+",
        "pay-per-view" : "Premiere",
        "ge tv" : "GE TV",
        "xsports": "Xsports",
        "hbo": "HBO",
        "record" : "Record",
        "sbt" : "SBT",
        "amazon": "Prime Video",
        "prime video": "Prime Video",
        "caze": "CazéTV",
        "cazetv": "CazéTV",
        "cazé tv": "CazéTV",
        "caze tv": "CazéTV",
        "paramount" : "Paramount+",
        "paramount+" : "Paramount+",
        "goat" : "GOAT",
        "sportynet" : "SportyNet",
        "record plus" : "RECORD PLUS",
        "portal r7" : "PORTAL R7",
        "apple tv" : "Apple TV"

    }

    achados = set() 
    
    texto_limpo = texto_bruto.lower()

    for termo, nome_exibicao in MAPEAMENTO.items():
        if termo in texto_limpo:
            achados.add(nome_exibicao) 

    if achados:
        lista_final = sorted(list(achados))
        return " " + ", ".join(lista_final)
    
    return " Canais não identificados"



def buscar_transmissao_doentes_direto(time_casa, time_fora, horario_previsto):
    url = "https://doentesporfutebol.com.br/guiadejogos/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return "📺 Consultar guia"

        soup = BeautifulSoup(response.text, 'html.parser')
        paragrafos = soup.find_all('p')
        
        jogos_validos = []

        for p in paragrafos:
            texto_limpo = p.get_text(separator=" ").lower()
            
            casa_simples = time_casa.lower().replace(".", "").strip()
            fora_simples = time_fora.lower().replace(".", "").strip()
            

            casa_curto = casa_simples.split()[-1] 
            fora_curto = fora_simples.split()[-1]

            contem_casa = casa_curto in texto_limpo
            contem_fora = fora_curto in texto_limpo
            contem_horario = horario_previsto in texto_limpo

            if contem_casa or contem_fora:
                if contem_horario:
                    print(f"✅ MATCH: {time_casa} x {time_fora} encontrado às {horario_previsto}")
                    return extrair_canais_mapeados(texto_limpo)
                else:
                    print(f"🕒 HORA ERRADA: Achei algo relacionado a {time_casa}/{time_fora}, mas o texto é: '{texto_limpo[:40]}...'")

        if jogos_validos:
            # Retorna o(s) canal(is) do jogo que bateu o horário
            return " / ".join(set(jogos_validos))

        return "📺 Canais não identificadosss"

    except Exception as e:
        print(f"❌ Erro no Scraping: {e}")
        return "📺 Erro ao processar guia"

def buscar_jogos_do_dia():
    """Busca jogos na API-Football e adiciona a transmissão via Scraping com Fallback do Banco"""
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {'x-apisports-key': FOOTBALL_API_KEY}
    params = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timezone": "America/Sao_Paulo"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        jogos = []
        for item in data.get("response", []):
            # IDs: 71 (Série A), 72 (Série B), 13 (Libertadores), 2 (Champions)
            if item["league"]["id"] in [71, 72, 13, 2]:
                
                id_casa_api = item["teams"]["home"]["id"]
                id_fora_api = item["teams"]["away"]["id"]
                
                name_casa_api = item["teams"]["home"]["name"]
                name_fora_api = item["teams"]["away"]["name"]
                
                horario_previsto = datetime.fromisoformat(item["fixture"]["date"]).strftime("%H:%M")
                

                termo_busca_casa = obter_termo_busca_time(id_casa_api) or name_casa_api
                termo_busca_fora = obter_termo_busca_time(id_fora_api) or name_fora_api
                
                print(f"🔄 Tradução: {name_casa_api} -> {termo_busca_casa} | {name_fora_api} -> {termo_busca_fora}")
                
                transmissao = buscar_transmissao_doentes_direto(termo_busca_casa, termo_busca_fora, horario_previsto)
                
                jogos.append({
                    "casa": name_casa_api,
                    "fora": name_fora_api,
                    "horario": horario_previsto,
                    "liga": item["league"]["name"],
                    "transmissao": transmissao
                })
        return jogos
    except Exception as e:
        print(f"❌ Erro ao buscar jogos e processar transmissão: {e}")
        return []
    











def schedule_fixtures():
    url = "https://v3.football.api-sports.io/fixtures"
    day = datetime.now()
    headers = {'x-apisports-key': FOOTBALL_API_KEY}
    params = {
        "date": day.strftime("%Y-%m-%d"),
        "timezone": "America/Sao_Paulo"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        for item in data.get("response", []):
            
            id_home_api = item["teams"]["home"]["id"]
            id_away_api = item["teams"]["away"]["id"]

            id_league = item["league"]["id"]
            
            horario = datetime.fromisoformat(item["fixture"]["date"]).strftime("%H:%M")

            conn = obter_conexao()
            cursor = conn.cursor()

            query = "INSERT INTO fixtures(id_home_api,id_away_api,id_league_api,game_date,game_time,status) VALUES (%s,%s,%s,%s,%s);"
            cursor.execute(query,(id_home_api,id_away_api,id_league,day,horario,None,))
        conn.commit()
        print(f"Tabela Fixtures preenchida para {day.strftime("%Y-%m-%d")}")

    except Exception as e:
            print(f"❌ Erro no Scraping: {e}")
            return "📺 Erro ao processar guia"
    




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





def buscar_jogos_do_dia():
    """Busca jogos na API-Football e adiciona a transmissão via Scraping com Fallback do Banco"""
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {'x-apisports-key': FOOTBALL_API_KEY}
    params = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timezone": "America/Sao_Paulo"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        jogos = []
        for item in data.get("response", []):
            # IDs: 71 (Série A), 72 (Série B), 13 (Libertadores), 2 (Champions)
            if item["league"]["id"] in [71, 72, 13, 2]:
                
                id_casa_api = item["teams"]["home"]["id"]
                id_fora_api = item["teams"]["away"]["id"]
                
                name_casa_api = item["teams"]["home"]["name"]
                name_fora_api = item["teams"]["away"]["name"]
                
                horario_previsto = datetime.fromisoformat(item["fixture"]["date"]).strftime("%H:%M")
                

                termo_busca_casa = obter_termo_busca_time(id_casa_api) or name_casa_api
                termo_busca_fora = obter_termo_busca_time(id_fora_api) or name_fora_api
                
                print(f"🔄 Tradução: {name_casa_api} -> {termo_busca_casa} | {name_fora_api} -> {termo_busca_fora}")
                
                transmissao = buscar_transmissao_doentes_direto(termo_busca_casa, termo_busca_fora, horario_previsto)
                
                jogos.append({
                    "casa": name_casa_api,
                    "fora": name_fora_api,
                    "horario": horario_previsto,
                    "liga": item["league"]["name"],
                    "transmissao": transmissao
                })
        return jogos
    except Exception as e:
        print(f"❌ Erro ao buscar jogos e processar transmissão: {e}")
        return []
    
