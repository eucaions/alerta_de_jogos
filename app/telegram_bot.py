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
bot = telebot.TeleBot(TOKEN) if TOKEN else None


def processar_update_telegram(update_json: dict):
    """Recebe o JSON do Webhook do Telegram e processa os handlers."""
    if not bot:
        print("⚠️ [WEBHOOK] Bot não instanciado!")
        return
        
    try:
        update = telebot.types.Update.de_json(update_json)
        print(f"🔄 [WEBHOOK] Processando update ID: {update.update_id}")
        bot.process_new_updates([update])
        print("✅ [WEBHOOK] Update processado pelo bot.")
    except Exception as e:
        print(f"❌ [WEBHOOK ERRO] Falha ao retransmitir update para o bot: {e}")
        traceback.print_exc()


def enviar_mensagem(texto_final: str, chat_id: str) -> bool:
    """Envia a agenda de jogos formatada para um chat_id do Telegram."""
    if not bot:
        return False
    try:
        bot.send_message(chat_id=chat_id, text=texto_final, parse_mode="HTML")
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
        times_favoritos = usuario[2]

        conjunto_mensagens = set()

        for team_id in times_favoritos:
            if team_id in mensagens_por_time:
                conjunto_mensagens.add(mensagens_por_time[team_id])

        if conjunto_mensagens:
            texto_final = "⚽ <b>SUA AGENDA DE JOGOS DE HOJE</b> ⚽\n\n"
            texto_final += "\n".join(conjunto_mensagens)
            enviar_mensagem(texto_final, chat_id)


# Registra os handlers no bot
if bot:
    @bot.message_handler(commands=['start'])
    def boas_vindas(message):
        print(f"📩 [HANDLER /START] Executando boas_vindas para {message.from_user.first_name}...")
        try:
            chat_id = str(message.chat.id)
            nome = message.from_user.first_name
            
            # 1. Tenta salvar/buscar no banco
            print("🗄️ [HANDLER /START] Consultando banco de dados...")
            user_id = obter_ou_criar_usuario_por_telegram(chat_id)
            print(f"🗄️ [HANDLER /START] Usuário ID interno: {user_id}")
            
            # 2. Monta o Link
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
            
            # 3. Envia a resposta
            bot.reply_to(message, texto, parse_mode="HTML", reply_markup=markup)
            print(f"✅ [HANDLER /START] Resposta enviada com sucesso no Telegram para {nome}!")

        except Exception as e:
            print(f"❌ [HANDLER /START ERRO]: {e}")
            traceback.print_exc()

    @bot.message_handler(func=lambda message: True)
    def escutar_qualquer_mensagem(message):
        print(f"📩 [HANDLER ECHO] Mensagem genérica recebida: {message.text}")
        try:
            bot.reply_to(message, f"Recebi sua mensagem: {message.text}")
        except Exception as e:
            print(f"❌ [HANDLER ECHO ERRO]: {e}")