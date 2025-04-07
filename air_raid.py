# air_raid.py
import os
import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext

load_dotenv()
ALERTS_IN_UA_TOKEN = os.getenv("ALERTS_IN_UA_TOKEN")
BASE_URL = "https://api.alerts.in.ua/v1/alerts/active.json"

# Клавиатура модуля "Воздушная тревога"
air_raid_keyboard = [['Проверить текущую тревогу'], ['Вернуться в главное меню']]
air_raid_reply_markup = ReplyKeyboardMarkup(air_raid_keyboard, resize_keyboard=True)

def show_air_raid_menu(update: Update, context: CallbackContext) -> None:
    """Отправляет меню воздушной тревоги."""
    update.message.reply_text("Выберите действие:", reply_markup=air_raid_reply_markup)

def check_air_raid(update: Update, context: CallbackContext) -> None:
    """Проверяет и отправляет информацию о текущих воздушных тревогах."""
    if not ALERTS_IN_UA_TOKEN:
        update.message.reply_text("API токен для проверки тревог не найден в файле .env.")
        return

    params = {"token": ALERTS_IN_UA_TOKEN}

    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        alerts_data = response.json()

        active_alerts = []
        for region, status in alerts_data.items():
            if status['enabled']:
                active_alerts.append(region)

        if active_alerts:
            message = "🚨 Внимание! Воздушная тревога объявлена в следующих областях:\n"
            message += "\n".join(active_alerts)
        else:
            message = "✅ На данный момент воздушных тревог нет."

        update.message.reply_text(message)

    except requests.exceptions.RequestException as e:
        update.message.reply_text(f"Ошибка при запросе данных о тревогах: {e}")
    except Exception as e:
        update.message.reply_text(f"Произошла непредвиденная ошибка при получении данных о тревогах: {e}")