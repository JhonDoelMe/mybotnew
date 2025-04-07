import os
import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
import logging

load_dotenv()
logger = logging.getLogger(__name__)

ALERTS_IN_UA_TOKEN = os.getenv("ALERTS_IN_UA_TOKEN")
BASE_URL = "https://api.alerts.in.ua/v1/alerts/active.json"

air_raid_keyboard = [['Проверить текущую тревогу'], ['Вернуться в главное меню']]
air_raid_reply_markup = ReplyKeyboardMarkup(air_raid_keyboard, resize_keyboard=True)

async def show_air_raid_menu(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Выберите действие:", reply_markup=air_raid_reply_markup)

async def check_air_raid(update: Update, context: CallbackContext) -> None:
    if not ALERTS_IN_UA_TOKEN:
        await update.message.reply_text("Не настроен токен для API тревог")
        return

    try:
        response = requests.get(BASE_URL, headers={"Authorization": ALERTS_IN_UA_TOKEN}, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, dict):
            raise ValueError("Invalid API response format")

        active_alerts = [region for region, status in data.items() if status.get('enabled')]
        
        if active_alerts:
            message = "🚨 Воздушная тревога в:\n" + "\n".join(active_alerts)
        else:
            message = "✅ Тревог нет"
            
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Air raid check error: {e}")
        await update.message.reply_text("Ошибка проверки тревог. Попробуйте позже.")