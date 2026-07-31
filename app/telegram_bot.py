import os
import telebot
import logging
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from app.database.queries import (
    obter_ou_criar_usuario_por_telegram,
    obter_todos_usuarios_com_favoritos
)

load_dotenv()

telebot.logger.setLevel(logging.CRITICAL)

TOKEN = os.getenv("TELEGRAM_TOKEN")

# Instancia o bot apenas se o TOKEN existir, evitando crash no startup
bot = telebot.TeleBot(TOKEN) if TOKEN else None


def enviar_mensagem(texto_final: str, chat_id: str) -> bool:
    """Envia a agenda de jogos formatada para um chat_id do Telegram."""
    if not bot:
        print("⚠️ Bot não inicializado. Verifique a variável TELEGRAM_TOKEN.")
        return False
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


# Registra o handler apenas se o bot estiver instanciado
if bot:
    @bot.message_handler(commands=['start'])
    def boas_vindas(message):
        try:
            chat_id = str(message.chat.id)
            nome = message.from_user.first_name
            
            user_id = obter_ou_criar_usuario_por_telegram(chat_id)
            
            base_url = os.getenv("APP_URL", "http://localhost:8000").rstrip("/")
            link_favoritos = f"{base_url}/favoritos/{chat_id}"
            
            markup = InlineKeyboardMarkup()
            btn_favoritos = InlineKeyboardButton(text="⚙️ Configurar Meus Times", url=link_favoritos)
            markup.add(btn_favoritos)
            
            texto = (
                f"Olá, <b>{nome}</b>! 👋\n\n"
                f"Seja bem-vindo ao seu assistente de <b>Transmissão de Futebol</b>!\n\n"
                f"Clique no botão abaixo para escolher seus times favoritos:"
            )
            
            bot.reply_to(message, texto, parse_mode="HTML", reply_markup=markup)
            print(f"✅ [HANDLER LOG] Resposta enviada com sucesso para {nome}")

        except Exception as e:
            print(f"❌ [HANDLER LOG] ERRO NO BOAS_VINDAS: {e}")


if __name__ == "__main__":
    if bot:
        print("🤖 Limpando webhooks antigos...")
        bot.remove_webhook()
        print("🤖 Bot do Telegram iniciado! Escutando mensagens...")
        bot.infinity_polling()
    else:
        print("❌ Não foi possível iniciar o bot localmente: TELEGRAM_TOKEN ausente no .env.")