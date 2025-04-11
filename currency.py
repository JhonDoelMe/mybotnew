import requests
import logging
from typing import Optional, List, Dict, Any
from cachetools import TTLCache

import telegram
from telegram.ext import ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

PRIVAT_API_URL = "https://api.privatbank.ua/p24api/pubinfo?exchange&json&coursid=5"
currency_cache = TTLCache(maxsize=1, ttl=3600)  # Cache for 1 hour

def get_currency_rates() -> Optional[List[Dict[str, Any]]]:
    """
    Fetches currency rates from PrivatBank API.

    Returns:
        Optional[List[Dict[str, Any]]]: List of currency rates or None on error.
    """
    if 'rates' in currency_cache:
        logger.info("Returning cached currency rates.")
        return currency_cache['rates']

    try:
        response = requests.get(PRIVAT_API_URL, timeout=10)
        response.raise_for_status()

        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list):
                    currency_cache['rates'] = data
                    return data
                logger.error(f"Unexpected data type: {type(data)}")
                return None
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON: {e}")
                return None
        else:
            logger.error(f"API request failed with status {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching currency rates: {e}")
        return None

def format_currency_message(rates: List[Dict[str, Any]]) -> str:
    """
    Formats a message with currency rates.

    Args:
        rates: List of currency rate dictionaries.

    Returns:
        str: Formatted message for Telegram.
    """
    if not rates:
        return "Не вдалося отримати курси валют."

    message = "Курс валют (готівка, ПриватБанк):\n\n"
    for rate in rates:
        ccy = rate.get('ccy')
        base_ccy = rate.get('base_ccy')
        buy = rate.get('buy')
        sale = rate.get('sale')
        if ccy and base_ccy and buy and sale:
            if ccy in ['USD', 'EUR']:
                message += f"🇺🇸 {ccy}/{base_ccy}:\n" \
                           f"   Купівля: {float(buy):.2f}\n" \
                           f"   Продаж:  {float(sale):.2f}\n\n"
    return message.strip()

async def get_currency_command(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for currency rates command.

    Args:
        update: Telegram update object.
        context: Telegram context.
    """
    rates = get_currency_rates()
    if rates:
        message = format_currency_message(rates)
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("Вибачте, не вдалося отримати актуальні курси валют.")