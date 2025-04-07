import os
import aiohttp
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
from database import get_connection, get_user_settings
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
WEATHER_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

async def get_weather(update: Update, context: CallbackContext):
    """Получить текущую погоду"""
    if not WEATHER_API_KEY:
        await update.message.reply_text("Ошибка: API-ключ для погоды не настроен")
        return
    
    user_id = update.effective_user.id
    with get_connection() as conn:
        settings = get_user_settings(conn, user_id)
        city = settings['city']
    
    try:
        params = {
            "q": city,
            "appid": WEATHER_API_KEY,
            "units": "metric",
            "lang": "ru"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(WEATHER_API_URL, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 404:
                    await update.message.reply_text(f"Город {city} не найден")
                    return
                response.raise_for_status()
                data = await response.json()
        
        description = data['weather'][0]['description'].capitalize()
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        humidity = data['main']['humidity']
        wind_speed = data['wind']['speed']
        wind_deg = data['wind'].get('deg', 0)
        
        wind_direction = deg_to_direction(wind_deg)
        
        message = (
            f"🌤️ Погода в {city}:\n"
            f"☁️ Состояние: {description}\n"
            f"🌡️ Температура: {temp}°C\n"
            f"🥶 Ощущается как: {feels_like}°C\n"
            f"💧 Влажность: {humidity}%\n"
            f"💨 Ветер: {wind_speed} м/с\n"
            f"🧭 Направление ветра: {wind_direction}"
        )
        
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Weather error: {e}")
        await update.message.reply_text("Ошибка получения погоды")

def deg_to_direction(deg):
    """Преобразование градусов в направление ветра"""
    directions = ["Север", "Северо-восток", "Восток", "Юго-восток", 
                  "Юг", "Юго-запад", "Запад", "Северо-запад"]
    idx = round(deg / 45) % 8
    return directions[idx]

async def handle_city_change(update: Update, context: CallbackContext):
    """Изменить город для погоды"""
    await update.message.reply_text("Введите название города:")
    context.user_data['awaiting_city'] = True

async def show_weather_menu(update: Update, context: CallbackContext):
    """Показать меню погоды"""
    keyboard = [['🌞 Текущая погода'], ['🏙️ Изменить город'], ['⬅️ Вернуться в главное меню']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Меню погоды", reply_markup=reply_markup)