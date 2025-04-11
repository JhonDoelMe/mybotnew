import logging
from typing import Optional, Dict
from datetime import datetime

import requests
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram import helpers

import config
import database as db

logger = logging.getLogger(__name__)

CURRENCY_API_URL = "https://api.exchangerate-api.com/v4/latest/UAH"
CURRENCY_CACHE: Dict[str, dict] = {}

async def get_currency_rates(force_update: bool = False) -> Optional[Dict[str, float]]:
    if not force_update and CURRENCY_CACHE and (datetime.now() - CURRENCY_CACHE['timestamp']).total_seconds() < 86400:
        logger.info("Returning cached currency rates.")
        return CURRENCY_CACHE['rates']

    try:
        response = requests.get(CURRENCY_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        CURRENCY_CACHE['rates'] = data['rates']
        CURRENCY_CACHE['timestamp'] = datetime.now()
        return data['rates']
    except requests.RequestException as e:
        logger.error(f"Failed to fetch currency rates: {e}")
        return None

async def get_currency_command(update: Update, context: ContextTypes.DEFAULT_TYPE, force_update: bool = False) -> None:
    user_id = update.effective_user.id
    rates = await get_currency_rates(force_update)
    if not rates:
        await update.message.reply_text("Не вдалося отримати курси валют.")
        return

    user_currencies = db.get_user_currencies(user_id) or ['USD', 'EUR']
    message = "💵 *Курси валют \\(UAH\\):*\n\n"  # Экранируем скобки
    for code in user_currencies:
        if code in rates:
            rate = rates[code]
            message += f"{helpers.escape_markdown(code, version=2)}: {1/rate:.2f} UAH\n"
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN_V2)

def add_currency_code(user_id: int, code: str) -> bool:
    if len(code) != 3 or not code.isalpha():
        return False
    rates = CURRENCY_CACHE.get('rates', {})
    if code not in rates:
        return False
    return db.add_user_currency(user_id, code.upper())

def get_user_currencies(user_id: int) -> Optional[list]:
    return db.get_user_currencies(user_id)