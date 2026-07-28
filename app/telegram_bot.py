import os
import requests
import telebot
from dotenv import load_dotenv
from app.database.queries import (
    obter_ou_criar_usuario_por_telegram,
    obter_todos_usuarios_com_favoritos
)

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)


def enviar_mensagem(texto_final: str, chat_id: str) -> bool:
    """Envia uma mensagem formatada via Telegram."""
    try:
        bot.send_message(chat_id=chat_id, text=texto_final, parse_mode="HTML")
        print(f"✅ Mensagem enviada com sucesso para chat_id: {chat_id}")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem para {chat_id}: {e}")
        return False


def disparar_agenda_matinal_usuarios(mensagens_por_time):
    """Percorre os usuários cadastrados e envia as agendas dos times favoritos."""
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


@bot.message_handler(commands=['start'])
def boas_vindas(message):
    chat_id = str(message.chat.id)
    nome = message.from_user.first_name
    
    # Registra/garante o usuário na tabela 'users'
    user_id = obter_ou_criar_usuario_por_telegram(chat_id)
    
    # Endereço da aplicação Web 
    DOMINIO_APP = os.getenv("APP_URL", "http://localhost:8000")
    link_favoritos = f"{DOMINIO_APP}/favoritos/{chat_id}"
    
    texto = (
        f"Olá, <b>{nome}</b>! 👋\n\n"
        f"Para escolher seus times do coração e receber a agenda matinal de jogos, "
        f"clique no link abaixo:\n\n"
        f"👉 <a href='{link_favoritos}'>Configurar Times Favoritos</a>"
    )
    
    bot.reply_to(message, texto, parse_mode="HTML")


if __name__ == "__main__":
    print("🤖 Bot do Telegram iniciado e escutando mensagens...")
    bot.infinity_polling()