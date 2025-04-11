# currency.py
import requests
import json
import logging
from typing import Optional, List, Dict, Any

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# URL API ПриватБанка для получения курсов наличной валюты
PRIVAT_API_URL = "https://api.privatbank.ua/p24api/pubinfo?exchange&json&coursid=5"

def get_currency_rates() -> Optional[List[Dict[str, Any]]]:
    """
    Получает курсы валют с API ПриватБанка.

    Returns:
        Optional[List[Dict[str, Any]]]: Список словарей с данными о курсах или None в случае ошибки.
    """
    try:
        response = requests.get(PRIVAT_API_URL, timeout=10)
        response.raise_for_status() # Проверка на HTTP ошибки

        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list):
                    return data
                else:
                    logger.error(f"Currency API returned unexpected data type: {type(data)}. Expected list.")
                    return None
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON response from Currency API: {e}")
                logger.debug(f"Response text: {response.text}")
                return None
            except Exception as e:
                 logger.error(f"An unexpected error occurred during JSON processing: {e}")
                 return None
        else:
            logger.error(f"Currency API request failed with status code {response.status_code}: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching currency rates: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred in get_currency_rates: {e}")
        return None

def format_currency_message(rates: List[Dict[str, Any]]) -> str:
    """
    Форматирует сообщение с курсами валют.

    Args:
        rates: Список словарей с данными о курсах.

    Returns:
        str: Отформатированное сообщение для пользователя.
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
            # Отображаем только USD и EUR для простоты
            if ccy in ['USD', 'EUR']:
                 message += f"🇺🇸 {ccy}/{base_ccy}:\n" \
                           f"   Купівля: {float(buy):.2f}\n" \
                           f"   Продаж:  {float(sale):.2f}\n\n"

    return message.strip()

async def get_currency_command(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для получения и отправки курсов валют."""
    rates = get_currency_rates()
    if rates:
        message = format_currency_message(rates)
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("Вибачте, не вдалося отримати актуальні курси валют.")