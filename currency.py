import os
import aiohttp
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
from database import get_connection, get_user_settings
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

CURRENCY_API_URL = "https://api.exchangerate-api.com/v4/latest/UAH"
CURRENCY_API_KEY = os.getenv("CURRENCY_API_KEY")

async def get_exchange_rate(update: Update, context: CallbackContext):
    """Получить курс валют"""
    user_id = update.effective_user.id
    with get_connection() as conn:
        settings = get_user_settings(conn, user_id)
        currency = update.message.text.split()[1] if len(update.message.text.split()) > 1 else settings['currency_preference']
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(CURRENCY_API_URL, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                data = await response.json()
        
        rate = data['rates'][currency]
        await update.message.reply_text(f"Курс {currency} к UAH: {rate:.2f}")
    except Exception as e:
        logger.error(f"Currency error: {e}")
        await update.message.reply_text("Ошибка получения курса валют")

async def show_currency_menu(update: Update, context: CallbackContext):
    """Показать меню валют"""
    keyboard = [['💲 USD'], ['€ EUR'], ['🔄 Изменить валюту'], ['⬅️ Вернуться в главное меню']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Меню валют", reply_markup=reply_markup)