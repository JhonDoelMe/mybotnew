import os
import aiohttp
import logging
from typing import Dict, Optional
from cachetools import TTLCache
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
from database import get_connection, get_user_settings, update_user_setting
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Конфигурация API
WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
WEATHER_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

# Кэширование на 10 минут
WEATHER_CACHE = TTLCache(maxsize=500, ttl=600)

# Константы
MAX_RETRIES = 3
REQUEST_TIMEOUT = 10

class WeatherAPI:
    @staticmethod
    async def get_weather_data(city: str) -> Optional[Dict]:
        """Получить данные о погоде с кэшированием"""
        if not WEATHER_API_KEY:
            raise ValueError("API key not configured")
            
        cache_key = city.lower()
        if cache_key in WEATHER_CACHE:
            return WEATHER_CACHE[cache_key]
            
        params = {
            "q": city,
            "appid": WEATHER_API_KEY,
            "units": "metric",
            "lang": "ru"
        }
        
        async with aiohttp.ClientSession() as session:
            for attempt in range(MAX_RETRIES):
                try:
                    async with session.get(
                        WEATHER_API_URL,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                    ) as response:
                        if response.status == 404:
                            return None
                        response.raise_for_status()
                        data = await response.json()
                        WEATHER_CACHE[cache_key] = data
                        return data
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    if attempt == MAX_RETRIES - 1:
                        raise

async def get_weather(update: Update, context: CallbackContext):
    """Получить текущую погоду"""
    if not WEATHER_API_KEY:
        await update.message.reply_text("⚠️ Сервис погоды временно недоступен")
        return
    
    user_id = update.effective_user.id
    with get_connection() as conn:
        settings = get_user_settings(conn, user_id)
        city = settings['city']
    
    if not city:
        await update.message.reply_text("ℹ️ Сначала укажите город с помощью кнопки '🏙️ Изменить город'")
        return
    
    try:
        data = await WeatherAPI.get_weather_data(city)
        if not data:
            await update.message.reply_text(f"❌ Город '{city}' не найден")
            return
        
        weather = data['weather'][0]
        main = data['main']
        wind = data['wind']
        
        message = (
            f"🌤️ Погода в {city}:\n\n"
            f"☁️ {weather['description'].capitalize()}\n"
            f"🌡️ Температура: {main['temp']:.1f}°C\n"
            f"🥶 Ощущается как: {main['feels_like']:.1f}°C\n"
            f"💧 Влажность: {main['humidity']}%\n"
            f"💨 Ветер: {wind['speed']} м/с, {_deg_to_direction(wind.get('deg', 0))}\n"
            f"🌄 Давление: {main['pressure']} hPa"
        )
        
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"Ошибка получения погоды: {e}")
        await update.message.reply_text("⚠️ Не удалось получить данные о погоде")

def _deg_to_direction(deg: int) -> str:
    """Преобразовать градусы в направление ветра"""
    directions = ["Северный", "Северо-восточный", "Восточный", "Юго-восточный", 
                 "Южный", "Юго-западный", "Западный", "Северо-западный"]
    idx = round(deg / 45) % 8
    return directions[idx]

async def handle_city_change(update: Update, context: CallbackContext):
    """Изменить город для погоды"""
    await update.message.reply_text("📍 Введите название города:")
    context.user_data['awaiting_city'] = True

async def handle_city_input(update: Update, context: CallbackContext):
    """Обработать ввод города пользователем"""
    user_id = update.effective_user.id
    city = update.message.text.strip()
    
    if len(city) < 2:
        await update.message.reply_text("❌ Название города слишком короткое")
        return
    
    with get_connection() as conn:
        update_user_setting(conn, user_id, 'city', city)
    
    await update.message.reply_text(f"✅ Город установлен: {city}")
    context.user_data.pop('awaiting_city', None)
    await show_weather_menu(update, context)

async def show_weather_menu(update: Update, context: CallbackContext):
    """Показать меню погоды"""
    user_id = update.effective_user.id
    with get_connection() as conn:
        settings = get_user_settings(conn, user_id)
        city_status = settings['city'] or "не указан"
    
    keyboard = [
        ['🌞 Текущая погода'],
        ['🏙️ Изменить город'],
        ['⬅️ Главное меню']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"🌤️ Меню погоды\n\n"
        f"Текущий город: {city_status}",
        reply_markup=reply_markup
    )