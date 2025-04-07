# currency.py
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext

NBU_EXCHANGE_RATE_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json"

# Клавиатура модуля "Курс валют"
currency_keyboard = [['USD', 'EUR'], ['Вернуться в главное меню']]
currency_reply_markup = ReplyKeyboardMarkup(currency_keyboard, resize_keyboard=True)

def show_currency_menu(update: Update, context: CallbackContext) -> None:
    """Отправляет меню курса валют."""
    update.message.reply_text("Выберите валюту:", reply_markup=currency_reply_markup)

def get_exchange_rate(update: Update, context: CallbackContext) -> None:
    """Получает и отправляет курс выбранной валюты."""
    try:
        response = requests.get(NBU_EXCHANGE_RATE_URL)
        response.raise_for_status()
        exchange_rates = response.json()

        text = update.message.text.upper()
        currency_data = None
        for rate in exchange_rates:
            if rate['cc'] == text:
                currency_data = rate
                break

        if currency_data:
            message = f"Курс {currency_data['cc']} к гривне (UAH) на {currency_data['exchangedate']}:\n"
            message += f"Покупка: {currency_data['rate']}"  # В API НБУ нет разделения на покупку и продажу, только средний курс
            update.message.reply_text(message)
        else:
            update.message.reply_text(f"Курс для валюты '{text}' не найден.")

    except requests.exceptions.RequestException as e:
        update.message.reply_text(f"Ошибка при запросе курса валют: {e}")
    except Exception as e:
        update.message.reply_text(f"Произошла непредвиденная ошибка при получении курса валют: {e}")