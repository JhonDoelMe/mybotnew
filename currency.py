import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
from database import get_connection, get_user_settings, update_user_setting
import logging

logger = logging.getLogger(__name__)

NBU_EXCHANGE_RATE_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json"

async def show_currency_menu(update: Update, context: CallbackContext):
    """Показать меню валют"""
    user_id = update.effective_user.id
    with get_connection() as conn:
        settings = get_user_settings(conn, user_id)
        
        keyboard = [
            ['USD', 'EUR'],
            ['Изменить валюту'],
            ['Вернуться в главное меню']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"Текущая валюта: {settings['currency_preference']}",
            reply_markup=reply_markup
        )

async def get_exchange_rate(update: Update, context: CallbackContext):
    """Получить курс валюты"""
    user_id = update.effective_user.id
    currency_code = update.message.text
    
    with get_connection() as conn:
        # Обновляем предпочтения пользователя
        update_user_setting(conn, user_id, 'currency_preference', currency_code)
        
        try:
            response = requests.get(NBU_EXCHANGE_RATE_URL, timeout=10)
            response.raise_for_status()
            rates = response.json()
            
            for rate in rates:
                if rate['cc'] == currency_code:
                    message = (
                        f"Курс {rate['cc']} к гривне на {rate['exchangedate']}:\n"
                        f"1 {rate['cc']} = {rate['rate']} UAH"
                    )
                    await update.message.reply_text(message)
                    return
            
            await update.message.reply_text("Валюта не найдена")
        except Exception as e:
            logger.error(f"Currency error: {e}")
            await update.message.reply_text("Ошибка получения курса")