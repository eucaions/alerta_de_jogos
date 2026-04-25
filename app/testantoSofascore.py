def buscar_jogos_do_dia():
    url = "https://v3.football.api-sports.io/fixtures"
    
    params = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timezone": "America/Sao_Paulo"
    }

    try:
        response = requests.get(url, headers=HEADERS, params=params)
        data = response.json()
        
        jogos = []
        for item in data.get("response", []):
            if item["league"]["id"] in [71, 72, 13, 2]:
                jogos.append({
                    "casa": item["teams"]["home"]["name"],
                    "fora": item["teams"]["away"]["name"],
                    "horario": datetime.fromisoformat(item["fixture"]["date"]).strftime("%H:%M"),
                    "liga": item["league"]["name"]
                })
        return jogos
    except Exception as e:
        print(f"Erro ao buscar: {e}")
        return []