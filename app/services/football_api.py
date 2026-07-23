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
from app.telegram_bot import enviar_mensagem

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
    
