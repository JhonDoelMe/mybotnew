import os
import requests
import time
from functools import lru_cache
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
import logging

load_dotenv()
logger = logging.getLogger(__name__)
NBU_EXCHANGE_RATE_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json"
CACHE_TIME = 3600  # 1 час

currency_keyboard = [['USD', 'EUR'], ['Вернуться в главное меню']]
currency_reply_markup = ReplyKeyboardMarkup(currency_keyboard, resize_keyboard=True)

@lru_cache(maxsize=1)
def get_cached_rates():
    """Кэширование курсов валют"""
    try:
        response = requests.get(NBU_EXCHANGE_RATE_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Currency API error: {e}")
        raise

async def show_currency_menu(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Выберите валюту:", reply_markup=currency_reply_markup)

async def get_exchange_rate(update: Update, context: CallbackContext) -> None:
    try:
        # Очистка кэша если устарел
        if get_cached_rates.cache_info().currsize > 0 and \
           time.time() - get_cached_rates.cache_info().created > CACHE_TIME:
            get_cached_rates.cache_clear()

        rates = get_cached_rates()
        currency_code = update.message.text.upper()
        
        for rate in rates:
            if rate['cc'] == currency_code:
                message = (f"Курс {rate['cc']} к гривне (UAH) на {rate['exchangedate']}:\n"
                          f"1 {rate['cc']} = {rate['rate']} UAH")
                await update.message.reply_text(message)
                return
        
        await update.message.reply_text(f"Курс для {currency_code} не найден")
    except Exception as e:
        logger.error(f"Exchange rate error: {e}")
        await update.message.reply_text("Ошибка получения курса валют. Попробуйте позже.")