from telethon import TelegramClient
from telegram import Update
from telegram.ext import CallbackContext
from database import get_connection, log_news_processed, is_news_processed
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
CONFIG_FILE = 'config.json'

async def show_tcc_news_menu(update: Update, context: CallbackContext):
    """Показать меню новостей"""
    keyboard = [
        ['Последние новости'],
        ['Вернуться в главное меню']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Новости ТЦК:", reply_markup=reply_markup)

async def get_tcc_news(update: Update, context: CallbackContext):
    """Получить новости ТЦК"""
    user_id = update.effective_user.id
    
    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
        
        client = TelegramClient('session', TELEGRAM_API_ID, TELEGRAM_API_HASH)
        await client.start()
        
        three_days_ago = datetime.now() - timedelta(days=3)
        news_messages = []
        
        with get_connection() as conn:
            for channel in config['telegram_channels']:
                async for message in client.iter_messages(channel['channel_id'], offset_date=three_days_ago):
                    if message.text and not is_news_processed(conn, user_id, message.text):
                        if any(kw.lower() in message.text.lower() for kw in channel['keywords']):
                            news_messages.append(message.text)
                            log_news_processed(conn, user_id, channel['channel_id'], message.text)
        
        if news_messages:
            message = "📰 Последние новости:\n\n" + "\n\n".join(news_messages[:5])  # Ограничение 5 новостей
            await update.message.reply_text(message[:4000])  # Ограничение длины
        else:
            await update.message.reply_text("Новых новостей не найдено")
            
        await client.disconnect()
    except Exception as e:
        logger.error(f"News error: {e}")
        await update.message.reply_text("Ошибка получения новостей")