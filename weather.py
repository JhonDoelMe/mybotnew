import os
import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
import logging

load_dotenv()
logger = logging.getLogger(__name__)

OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
CITY = "Kyiv,UA"  # Город по умолчанию

weather_keyboard = [['Текущая погода'], ['Сменить город'], ['Вернуться в главное меню']]
weather_reply_markup = ReplyKeyboardMarkup(weather_keyboard, resize_keyboard=True)

async def show_weather_menu(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Выберите действие:", reply_markup=weather_reply_markup)

async def get_weather(update: Update, context: CallbackContext) -> None:
    city = context.user_data.get('weather_city', CITY)
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

        if data.get("cod") != 200:
            raise ValueError(data.get("message", "Unknown error"))

        weather_info = {
            "city": data["name"],
            "temp": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "wind": data["wind"]["speed"],
            "description": data["weather"][0]["description"].capitalize(),
            "icon": data["weather"][0]["icon"]
        }

        emoji = get_weather_emoji(weather_info["description"])
        message = (
            f"{emoji} Погода в {weather_info['city']}:\n"
            f"{weather_info['description']}\n"
            f"Температура: {weather_info['temp']}°C (ощущается как {weather_info['feels_like']}°C)\n"
            f"Влажность: {weather_info['humidity']}%\n"
            f"Ветер: {weather_info['wind']} м/с"
        )
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Weather error: {e}")
        await update.message.reply_text("Ошибка получения погоды. Попробуйте позже.")

def get_weather_emoji(description: str) -> str:
    desc = description.lower()
    if "дождь" in desc: return "🌧️"
    elif "снег" in desc: return "❄️"
    elif "ясно" in desc: return "☀️"
    elif "облачно" in desc: return "☁️"
    elif "гроза" in desc: return "⛈️"
    else: return "🌤️"