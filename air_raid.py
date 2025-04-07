import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
from database import get_connection, get_user_settings, update_user_setting
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

ALERTS_API_URL = "https://api.alerts.in.ua/v1/alerts/active.json"
ALERTS_API_TOKEN = os.getenv("ALERTS_IN_UA_TOKEN")

async def show_air_raid_menu(update: Update, context: CallbackContext):
    """Показать меню тревог"""
    user_id = update.effective_user.id
    with get_connection() as conn:
        settings = get_user_settings(conn, user_id)
        
        status = "включены" if settings['notify_air_alerts'] else "выключены"
        keyboard = [
            ['Проверить тревоги'],
            ['Отключить уведомления' if settings['notify_air_alerts'] else 'Включить уведомления'],
            ['Вернуться в главное меню']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"Уведомления: {status}",
            reply_markup=reply_markup
        )

async def check_air_raid(update: Update, context: CallbackContext):
    """Проверить статус тревог"""
    try:
        headers = {"Authorization": ALERTS_API_TOKEN}
        response = requests.get(ALERTS_API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        alerts = response.json()
        
        active_alerts = [region for region, status in alerts.items() if status['enabled']]
        
        if active_alerts:
            message = "🚨 Тревога в регионах:\n" + "\n".join(active_alerts)
        else:
            message = "✅ Нет активных тревог"
            
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Air raid error: {e}")
        await update.message.reply_text("Ошибка проверки тревог")

async def toggle_notifications(update: Update, context: CallbackContext):
    """Переключить уведомления"""
    user_id = update.effective_user.id
    with get_connection() as conn:
        settings = get_user_settings(conn, user_id)
        new_status = not settings['notify_air_alerts']
        update_user_setting(conn, user_id, 'notify_air_alerts', int(new_status))
        
        status = "включены" if new_status else "выключены"
        await update.message.reply_text(f"Уведомления {status}")