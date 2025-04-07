import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
from database import get_connection, get_user_settings, update_user_setting
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

async def show_weather_menu(update: Update, context: CallbackContext):
    """Показать меню погоды"""
    user_id = update.effective_user.id
    with get_connection() as conn:
        settings = get_user_settings(conn, user_id)
        
        keyboard = [
            ['Текущая погода'],
            ['Изменить город'],
            ['Вернуться в главное меню']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"Текущий город: {settings['city']}",
            reply_markup=reply_markup
        )

async def get_weather(update: Update, context: CallbackContext):
    """Получить погоду для сохраненного города"""
    user_id = update.effective_user.id
    with get_connection() as conn:
        settings = get_user_settings(conn, user_id)
        city = settings['city']
        
        try:
            params = {
                "q": city,
                "appid": OPENWEATHERMAP_API_KEY,
                "units": "metric",
                "lang": "ru"
            }
            response = requests.get(BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            weather_info = {
                "city": data["name"],
                "temp": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "humidity": data["main"]["humidity"],
                "wind": data["wind"]["speed"],
                "description": data["weather"][0]["description"].capitalize()
            }

            emoji = get_weather_emoji(weather_info["description"])
            message = (
                f"{emoji} Погода в {weather_info['city']}:\n"
                f"{weather_info['description']}\n"
                f"Температура: {weather_info['temp']}°C\n"
                f"Ощущается как: {weather_info['feels_like']}°C\n"
                f"Влажность: {weather_info['humidity']}%\n"
                f"Ветер: {weather_info['wind']} м/с"
            )
            await update.message.reply_text(message)
        except Exception as e:
            logger.error(f"Weather error: {e}")
            await update.message.reply_text("Ошибка получения погоды")

async def handle_city_change(update: Update, context: CallbackContext):
    """Обработка изменения города"""
    if 'awaiting_city' in context.user_data:
        user_id = update.effective_user.id
        city = update.message.text
        
        with get_connection() as conn:
            update_user_setting(conn, user_id, 'city', city)
        
        del context.user_data['awaiting_city']
        await update.message.reply_text(f"Город изменен на {city}")
        await get_weather(update, context)
    else:
        await update.message.reply_text("Введите название города:")
        context.user_data['awaiting_city'] = True

def get_weather_emoji(description: str) -> str:
    """Получить emoji для погоды"""
    desc = description.lower()
    if "дождь" in desc: return "🌧️"
    elif "снег" in desc: return "❄️"
    elif "ясно" in desc: return "☀️"
    elif "облачно" in desc: return "☁️"
    elif "гроза" in desc: return "⛈️"
    else: return "🌤️"