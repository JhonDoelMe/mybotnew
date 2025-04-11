import os
import aiohttp
import logging
from typing import Dict, Optional
from cachetools import TTLCache
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
from database import get_connection, get_user_settings, update_user_setting
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Конфигурация API
CURRENCY_API_URL = "https://api.exchangerate-api.com/v4/latest/UAH"
CURRENCY_API_KEY = os.getenv("CURRENCY_API_KEY")

# Кэширование на 1 час
CURRENCY_CACHE = TTLCache(maxsize=10, ttl=3600)

# Поддерживаемые валюты
SUPPORTED_CURRENCIES = {
    'USD': '💵 Доллар США',
    'EUR': '€ Евро',
    'PLN': '🇵🇱 Польский злотый',
    'GBP': '🇬🇧 Фунт стерлингов'
}

class CurrencyAPI:
    @staticmethod
    async def get_exchange_rates() -> Optional[Dict]:
        """Получить текущие курсы валют"""
        if not CURRENCY_API_KEY:
            raise ValueError("API key not configured")
            
        if 'rates' in CURRENCY_CACHE:
            return CURRENCY_CACHE['rates']
            
        headers = {"Authorization": f"Bearer {CURRENCY_API_KEY}"} if CURRENCY_API_KEY else {}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    CURRENCY_API_URL,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    CURRENCY_CACHE['rates'] = data['rates']
                    return data['rates']
            except Exception as e:
                logger.error(f"Ошибка получения курсов валют: {e}")
                return None

async def get_exchange_rate(update: Update, context: CallbackContext):
    """Получить курс валюты"""
    user_id = update.effective_user.id
    with get_connection() as conn:
        settings = get_user_settings(conn, user_id)
        
        # Определяем запрошенную валюту
        text = update.message.text
        if text in ('💲 USD', '€ EUR'):
            currency = text.split()[1] if text.startswith('€') else 'USD'
        else:
            currency = settings['currency_preference']

    if currency not in SUPPORTED_CURRENCIES:
        await update.message.reply_text("❌ Валюта не поддерживается")
        return
    
    try:
        rates = await CurrencyAPI.get_exchange_rates()
        if not rates:
            raise ValueError("Не удалось получить курсы валют")
            
        rate = rates.get(currency)
        if not rate:
            raise ValueError(f"Курс для {currency} не найден")
            
        await update.message.reply_text(
            f"{SUPPORTED_CURRENCIES[currency]}\n"
            f"➡️ 1 {currency} = {float(rate):.2f} UAH\n"
            f"⬅️ 1 UAH = {1/float(rate):.4f} {currency}"
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения курса: {e}")
        await update.message.reply_text("⚠️ Не удалось получить курс валюты")

async def show_currency_menu(update: Update, context: CallbackContext):
    """Показать меню валют"""
    user_id = update.effective_user.id
    with get_connection() as conn:
        settings = get_user_settings(conn, user_id)
        currency_status = settings['currency_preference']
    
    keyboard = [
        ['💲 USD', '€ EUR'],
        ['🇵🇱 PLN', '🇬🇧 GBP'],
        ['🔄 Изменить валюту'],
        ['⬅️ Главное меню']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"💱 Меню валют\n\n"
        f"Текущая валюта: {SUPPORTED_CURRENCIES.get(currency_status, currency_status)}",
        reply_markup=reply_markup
    )

async def handle_currency_change(update: Update, context: CallbackContext):
    """Обработать изменение валюты"""
    text = update.message.text
    if text == '🔄 Изменить валюту':
        await _show_currency_selection(update)
    elif text in SUPPORTED_CURRENCIES:
        user_id = update.effective_user.id
        currency = text.split()[1] if text.startswith('€') else text.split()[0]
        
        with get_connection() as conn:
            update_user_setting(conn, user_id, 'currency_preference', currency)
            await update.message.reply_text(
                f"✅ Валюта изменена на {SUPPORTED_CURRENCIES[currency]}"
            )
            await show_currency_menu(update, context)

async def _show_currency_selection(update: Update):
    """Показать выбор валюты"""
    keyboard = [
        ['💲 USD', '€ EUR'],
        ['🇵🇱 PLN', '🇬🇧 GBP'],
        ['⬅️ Назад']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Выберите предпочитаемую валюту:",
        reply_markup=reply_markup
    )