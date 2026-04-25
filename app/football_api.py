import requests
from datetime import datetime
import os
import json
from dotenv import load_dotenv

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
        "tnt" : "TNT",
        "disney": "Disney+",
        "disney+": "Disney+",
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
        "caze tv": "CazéTV"
    }

    achados = set() 
    
    texto_limpo = texto_bruto.lower()

    for termo, nome_exibicao in MAPEAMENTO.items():
        if termo in texto_limpo:
            achados.add(nome_exibicao) 

    if achados:
        # Convertemos de volta para lista para ordenar e formatar como string
        lista_final = sorted(list(achados))
        return " " + ", ".join(lista_final)
    
    return " Canais não identificados"





def buscar_transmissao_serper(time_casa, time_fora):
    url = "https://google.serper.dev/search"
    query = f"onde assistir {time_casa} x {time_fora} hoje transmissão brasil"
    
    payload = json.dumps({
        "q": query,
        "gl": "br",
        "hl": "pt-br",
        "autocorrect": True
    })
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        results = response.json()
        
        # Tenta pegar a resposta direta do Google (Answer Box)
        texto_busca = ""
        if "answerBox" in results:
            texto_busca = results["answerBox"].get("snippet") or results["answerBox"].get("answer")
        elif "organic" in results:
            texto_busca = results["organic"][0].get("snippet")

        return extrair_canais_mapeados(texto_busca)

    except Exception as e:
        print(f"Erro no Serper: {e}")
    return "Pesquisar no Google"










def buscar_jogos_do_dia():
    """Busca jogos na API-Football e adiciona a transmissão via Serper"""
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
                time_casa = item["teams"]["home"]["name"]
                time_fora = item["teams"]["away"]["name"]
                
                # CHAMADA DO SERPER: Aqui acontece a mágica
                transmissao = buscar_transmissao_serper(time_casa, time_fora)
                
                jogos.append({
                    "casa": time_casa,
                    "fora": time_fora,
                    "horario": datetime.fromisoformat(item["fixture"]["date"]).strftime("%H:%M"),
                    "liga": item["league"]["name"],
                    "transmissao": transmissao
                })
        return jogos
    except Exception as e:
        print(f"Erro ao buscar: {e}")
        return []