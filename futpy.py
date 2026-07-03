import os
from dotenv import load_dotenv
import requests
from datetime import date
import pandas as pd


load_dotenv()
FUT_PYTHON_KEY = os.getenv("FUT_PYTHON_KEY")
DIA = date.today().isoformat()

def live_games():
    url = f"https://futpythontrader.com.br/api/jogos-do-dia?date={DIA}&format=csv&api_key={FUT_PYTHON_KEY}"
    jogos_do_dia = pd.read_csv(url)
    print(jogos_do_dia)
if __name__ == "__main__":
    live_games()