import logging
from typing import Optional
from datetime import datetime

import requests
from telegram import Update
from telegram.ext import ContextTypes

import config

logger = logging.getLogger(__name__)

WEATHER_API_KEY = config.cfg.get('WEATHER_API_KEY')
WEATHER_API_URL = "http://api.openweathermap.org/data/2.5/weather"
WEATHER_CACHE: dict = {}

async def get_weather(city: str, force_update: bool = False) -> Optional[str]:
    if not WEATHER_API_KEY:
        logger.error("Weather API key is not configured.")
        return None

    cache_key = city.lower()
    if not force_update and cache_key in WEATHER_CACHE:
        cached = WEATHER_CACHE[cache_key]
        if (datetime.now() - cached['timestamp']).total_seconds() < 3600:
            logger.info(f"Returning cached weather for {city}")
            return cached['data']

    params = {
        'q': city,
        'appid': WEATHER_API_KEY,
        'units': 'metric',
        'lang': 'ua'
    }
    try:
        response = requests.get(WEATHER_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        weather_desc = data['weather'][0]['description']
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        humidity = data['main']['humidity']
        wind_speed = data['wind']['speed']

        result = (
            f"Погода в {city}:\n"
            f"📌 {weather_desc.capitalize()}\n"
            f"🌡️ Температура: {temp}°C (відчувається як {feels_like}°C)\n"
            f"💧 Вологість: {humidity}%\n"
            f"💨 Вітер: {wind_speed} м/с"
        )
        WEATHER_CACHE[cache_key] = {'data': result, 'timestamp': datetime.now()}
        return result
    except requests.RequestException as e:
        logger.error(f"Failed to fetch weather for {city}: {e}")
        return None

async def get_weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE, force_update: bool = False) -> None:
    try:
        city = context.user_data.get('city', 'Kyiv')
        if context.args:
            city = " ".join(context.args)
            context.user_data['city'] = city

        logger.info(f"Fetching weather for {city}")
        weather_data = await get_weather(city, force_update)
        if weather_data:
            await update.message.reply_text(weather_data)
        else:
            await update.message.reply_text(f"Не вдалося отримати погоду для {city}. Перевірте ключ API погоди.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Помилка: {str(e)}")
        raise