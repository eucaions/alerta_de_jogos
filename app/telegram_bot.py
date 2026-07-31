import os
import telebot
import logging
import traceback
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from app.database.queries import (
    obter_ou_criar_usuario_por_telegram,
    obter_todos_usuarios_com_favoritos
)

load_dotenv()

telebot.logger.setLevel(logging.CRITICAL)

TOKEN = os.getenv("TELEGRAM_TOKEN")

# Instância única global do Bot
bot = telebot.TeleBot(TOKEN) if TOKEN else None


def processar_update_telegram(update_json: dict):
    """Recebe o dicionário do FastAPI e repassa para os handlers do telebot."""
    if not bot:
        print("⚠️ [BOT] Instância do bot não encontrada (TELEGRAM_TOKEN ausente).")
        return
        
    try:
        update = telebot.types.Update.de_json(update_json)
        if update:
            print(f"🔄 [BOT] Processando mensagem do chat_id: {update.message.chat.id if update.message else 'N/A'}")
            bot.process_new_updates([update])
    except Exception as e:
        print(f"❌ [BOT ERRO] Falha ao processar update: {e}")
        traceback.print_exc()


def enviar_mensagem(texto_final: str, chat_id: str) -> bool:
    """Envia mensagem direta para um chat_id."""
    if not bot:
        return False
    try:
        bot.send_message(chat_id=chat_id, text=texto_final, parse_mode="HTML")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem para {chat_id}: {e}")
        return False


def disparar_agenda_matinal_usuarios(mensagens_por_time):
    """Dispara o resumo dos jogos para os usuários cadastrados."""
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


# ==========================================================
# REGISTRO DE HANDLERS (Declarados diretamente no escopo)
# ==========================================================
if bot:
    @bot.message_handler(commands=['start'])
    def boas_vindas(message):
        print(f"📩 [HANDLER /START] Chamado por {message.from_user.first_name} ({message.chat.id})")
        try:
            chat_id = str(message.chat.id)
            nome = message.from_user.first_name
            
            user_id = obter_ou_criar_usuario_por_telegram(chat_id)
            
            base_url = os.getenv("APP_URL", "https://jogos-alert-web.onrender.com").rstrip("/")
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
            print(f"✅ [HANDLER /START] Resposta enviada com sucesso no Telegram!")

        except Exception as e:
            print(f"❌ [HANDLER /START ERRO]: {e}")
            traceback.print_exc()

    @bot.message_handler(func=lambda message: True)
    def escutar_qualquer_mensagem(message):
        print(f"📩 [HANDLER ECHO] Recebido: '{message.text}' de {message.from_user.first_name}")
        try:
            bot.reply_to(message, f"Recebi sua mensagem: {message.text}")
        except Exception as e:
            print(f"❌ [HANDLER ECHO ERRO]: {e}")