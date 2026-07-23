import requests
import os
from dotenv import load_dotenv
from app.database.queries import obter_todos_usuarios_com_favoritos

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def enviar_mensagem(texto_final: str, chat_id: str):

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": texto_final
    }

    response = requests.post(url, data=payload)

    print("STATUS:", response.status_code)


def disparar_agenda_matinal_usuarios(mensagens_por_time):

    usuarios = obter_todos_usuarios_com_favoritos()

    for usuario in usuarios:
        chat_id = usuario[1]
        times_favoritos = usuario[2]

        conjunto_mensagens = set()

        for team_id in times_favoritos:

            if team_id in mensagens_por_time:
                conjunto_mensagens.add(mensagens_por_time[team_id])

        if conjunto_mensagens:
            texto_final = "⚽ <b>SUA AGENDA DE JOGOS DE HOJE</b> ⚽\n\n"
            texto_final += "\n".join(conjunto_mensagens)
            enviar_mensagem(texto_final, chat_id)