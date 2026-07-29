import os
import telebot
from dotenv import load_dotenv
from app.database.queries import obter_ou_criar_usuario_por_telegram, obter_todos_usuarios_com_favoritos

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)


def enviar_mensagem(texto_final: str, chat_id: str) -> bool:
    """Envia a agenda de jogos formatada para um chat_id do Telegram."""
    try:
        bot.send_message(chat_id=chat_id, text=texto_final, parse_mode="HTML")
        print(f"✅ Mensagem enviada com sucesso para chat_id: {chat_id}")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem para {chat_id}: {e}")
        return False


def disparar_agenda_matinal_usuarios(mensagens_por_time):
    """Percorre os usuários cadastrados e envia a agenda dos times favoritos."""
    usuarios = obter_todos_usuarios_com_favoritos()

    if not usuarios:
        print("ℹ️ Nenhum usuário com favoritos encontrado para envio.")
        return

    for usuario in usuarios:
        chat_id = usuario[1]
        times_favoritos = usuario[2]  # Lista de IDs de API dos times favoritos

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
    try:
        chat_id = str(message.chat.id)
        nome = message.from_user.first_name
        
        # 1. Garante que o usuário existe no PostgreSQL
        user_id = obter_ou_criar_usuario_por_telegram(chat_id)
        
        # 2. Pega o endereço base configurado
        base_url = os.getenv("APP_URL", "http://localhost:8000").rstrip("/")
        link_favoritos = f"{base_url}/favoritos/{chat_id}"
        
        # 3. Monta o texto garantindo o HTML sem quebras na tag <a>
        texto = (
            f"Olá, <b>{nome}</b>! 👋\n\n"
            f"Seja bem-vindo ao seu assistente de <b>Transmissão de Futebol</b>!\n\n"
            f"Acesse o link abaixo no seu navegador para escolher seus times favoritos:\n\n"
            f"{link_favoritos}"
        )
        
        bot.reply_to(message, texto, parse_mode="HTML")
        print(f"✅ Resposta enviada com sucesso para {nome} com o link: {link_favoritos}")

    except Exception as e:
        print(f"❌ ERRO NO BOAS_VINDAS: {e}")


if __name__ == "__main__":
    print("🤖 Limpando webhooks antigos...")
    bot.remove_webhook()
    print("🤖 Bot do Telegram iniciado! Escutando mensagens...")
    bot.infinity_polling()