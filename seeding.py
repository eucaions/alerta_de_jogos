import requests
import pandas as pd

URL = "https://api.football-data.org/v4/competitions/BSA/standings"

HEADERS = {
    'X-Auth-Token': "503aa5af4a8a499eb0395233917af352" 
}

response = requests.get(URL, headers=HEADERS, timeout=15)


if response.status_code == 200:
    dados = response.json()
    tabela = dados['standings'][0]['table']
    
    for time in tabela:
        print(f"{time['position']}º - {time['team']['name']} ({time['points']} pts)")
else:
    print(f"Erro na requisição: {response.status_code}")