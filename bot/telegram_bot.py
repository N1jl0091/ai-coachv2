"""
bot/telegram_bot.py
Telegram bot initialisation and message routing.
"""
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from bot.commands import (
    start_command,
    status_command,
    profile_command,
    setup_conversation_handler,
)
from bot.session import get_session, update_session
from coach.ai import get_coach_reply


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_message = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        session = get_session(user_id)
        reply, updated_session = await get_coach_reply(
            telegram_id=user_id,
            user_message=user_message,
            session_history=session["history"],
        )
        update_session(user_id, updated_session)
    except Exception as e:
        reply = f"Sorry, something went wrong: {str(e)}"
    await update.message.reply_text(reply, parse_mode="Markdown")

def create_bot() -> Application:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("profile", profile_command))

    # /setup conversational onboarding
    app.add_handler(setup_conversation_handler())

    # Free-form messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Error handler — logs instead of crashing
    async def error_handler(update, context):
        import logging
        logging.error(f"Bot error: {context.error}")

    app.add_error_handler(error_handler)

    return app
