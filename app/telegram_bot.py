import requests
import os
from dotenv import load_dotenv
from app.database.queries import obter_todos_usuarios_com_favoritos

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")

def enviar_mensagem(texto_final: str, chat_id: str) -> bool:

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": texto_final,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, data=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Mensagem enviada com sucesso para chat_id: {chat_id}")
            return True
        else:
            print(f"⚠️ Falha no envio para {chat_id}. Status: {response.status_code}, Resposta: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Erro HTTP ao conectar com Telegram: {e}")
        return False


def disparar_agenda_matinal_usuarios(mensagens_por_time):

    usuarios = obter_todos_usuarios_com_favoritos()

    if not usuarios:
        print("ℹ️ Nenhum usuário com favoritos encontrado para envio.")
        return

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