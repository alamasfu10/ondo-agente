"""El agente de Ondo en un bot de Telegram.

    uv run python -m canales.telegram_bot

Funciona en modo polling: el programa pregunta a Telegram cada poco si hay
mensajes nuevos. La conexión sale de tu portátil, así que no hace falta una
URL pública. Necesitas TELEGRAM_BOT_TOKEN en el .env (te lo da @BotFather).

Comandos del bot: /start (bienvenida) y /reset (conversación nueva).
Las opciones del agente se muestran como botones bajo el mensaje.
"""

import logging
import os

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler,
                          filters)

from agente.agente import AgenteOndo
from agente.herramientas import RAIZ

load_dotenv(RAIZ / ".env")
logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("ondo")

BIENVENIDA = (
    "¡Hola! Soy el asistente virtual de Ondo, una inteligencia artificial. Puedo decirte dónde está tu pedido, "
    "ayudarte con una devolución o reservarte cita en un taller asociado. Si en algún momento prefieres hablar "
    "con una persona, solo tienes que decírmelo. ¿En qué te ayudo?"
)


def teclado(opciones: list[str]) -> InlineKeyboardMarkup | None:
    if not opciones:
        return None
    # Telegram limita callback_data a 64 bytes: guardamos el índice y recuperamos el texto al pulsar.
    return InlineKeyboardMarkup([[InlineKeyboardButton(op, callback_data=str(i))] for i, op in enumerate(opciones)])


async def contestar(update: Update, context: ContextTypes.DEFAULT_TYPE, texto: str) -> None:
    agente: AgenteOndo = context.application.bot_data["agente"]
    chat_id = str(update.effective_chat.id)
    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    try:
        r = await agente.responder(f"telegram-{chat_id}", texto)
    except Exception:
        log.exception("Error del agente")
        await context.bot.send_message(update.effective_chat.id,
                                       "Perdona, he tenido un problema técnico. ¿Puedes repetirlo?")
        return
    context.chat_data["opciones"] = r.opciones
    log.info("chat %s | cliente: %s | ondo: %s", chat_id, texto, r.texto[:80])
    await context.bot.send_message(update.effective_chat.id, r.texto, reply_markup=teclado(r.opciones))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.application.bot_data["agente"].reiniciar(f"telegram-{update.effective_chat.id}")
    await update.message.reply_text(BIENVENIDA)


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.application.bot_data["agente"].reiniciar(f"telegram-{update.effective_chat.id}")
    await update.message.reply_text("Conversación nueva. ¿En qué te ayudo?")


async def mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await contestar(update, context, update.message.text)


async def boton(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    opciones = context.chat_data.get("opciones") or []
    i = int(q.data)
    if i >= len(opciones):
        return
    await q.edit_message_reply_markup(None)  # quita los botones del mensaje anterior
    await context.bot.send_message(update.effective_chat.id, f"» {opciones[i]}")
    await contestar(update, context, opciones[i])


async def al_arrancar(app: Application) -> None:
    app.bot_data["agente"] = await AgenteOndo().__aenter__()
    yo = await app.bot.get_me()
    log.info("Bot @%s listo. Escríbele en Telegram (Ctrl+C para parar).", yo.username)


async def al_parar(app: Application) -> None:
    await app.bot_data["agente"].__aexit__(None, None, None)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Falta TELEGRAM_BOT_TOKEN en el .env. Créalo con @BotFather (guía del día 1).")
    app = Application.builder().token(token).post_init(al_arrancar).post_shutdown(al_parar).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CallbackQueryHandler(boton))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
