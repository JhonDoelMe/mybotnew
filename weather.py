import requests
import logging
from typing import Optional, Dict, Any
from cachetools import TTLCache

import telegram
from telegram import helpers
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import config
from constants import DEFAULT_CITY

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

WEATHER_API_URL = "http://api.openweathermap.org/data/2.5/weather"
weather_cache = TTLCache(maxsize=100, ttl=600)  # Cache for 10 minutes

def get_weather(city: str) -> Optional[Dict[str, Any]]:
    """
    Fetches weather data for a city from OpenWeatherMap API.

    Args:
        city: Name of the city.

    Returns:
        Optional[Dict[str, Any]]: Weather data dictionary or None on error.
    """
    cache_key = city.lower()
    if cache_key in weather_cache:
        logger.info(f"Returning cached weather for {city}")
        return weather_cache[cache_key]

    api_key = config.cfg.get('WEATHER_API_KEY')
    if not api_key:
        logger.error("WEATHER_API_KEY not configured.")
        return None

    params = {'q': city, 'appid': api_key, 'units': 'metric', 'lang': 'uk'}

    try:
        response = requests.get(WEATHER_API_URL, params=params, timeout=10)
        response.raise_for_status()

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                weather_cache[cache_key] = data
                return data
            logger.error(f"Unexpected data type: {type(data)}")
            return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"City '{city}' not found.")
            return {'cod': '404', 'message': 'city not found'}
        logger.error(f"HTTP error fetching weather for {city}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error fetching weather for {city}: {e}")
        return None

def format_weather_message(weather_data: Dict[str, Any]) -> str:
    """
    Formats weather data into a Telegram message.

    Args:
        weather_data: Weather data dictionary.

    Returns:
        str: Formatted message.
    """
    if not weather_data or weather_data.get('cod') != 200:
        if weather_data and weather_data.get('cod') == '404':
            return "На жаль, не можу знайти інформацію для такого міста."
        return "Вибачте, не вдалося отримати дані про погоду."

    city_name = helpers.escape_markdown(weather_data.get('name', 'Невідоме місто'), version=2)
    main_info = weather_data.get('main', {})
    weather_desc_list = weather_data.get('weather', [])
    wind_info = weather_data.get('wind', {})

    temp = main_info.get('temp')
    feels_like = main_info.get('feels_like')
    humidity = main_info.get('humidity')
    pressure_hpa = main_info.get('pressure')
    wind_speed = wind_info.get('speed')
    description = helpers.escape_markdown(
        weather_desc_list[0].get('description', 'невідомо') if weather_desc_list else 'невідомо',
        version=2
    )
    icon_code = weather_desc_list[0].get('icon', '') if weather_desc_list else ''

    weather_icons = {
        "01d": "☀️", "01n": "🌙", "02d": "⛅️", "02n": "☁️", "03d": "☁️", "03n": "☁️",
        "04d": "☁️", "04n": "☁️", "09d": "🌦", "09n": "🌧", "10d": "🌧", "10n": "🌧",
        "11d": "⛈", "11n": "⛈", "13d": "❄️", "13n": "❄️", "50d": "🌫", "50n": "🌫"
    }
    weather_emoji = weather_icons.get(icon_code, "")
    pressure_mmhg = int(pressure_hpa * 0.750062) if pressure_hpa is not None else None

    def format_and_escape(value: Optional[float], precision: int = 1) -> str:
        if value is None:
            return "N/A"
        return f"{value:.{precision}f}".replace('.', '\\.')

    message = f"*Погода в місті* {city_name}:\n\n"
    message += f"{weather_emoji} {description.capitalize()}\n"
    if temp is not None:
        message += f"🌡 Температура: `{format_and_escape(temp)}°C`\n"
    if feels_like is not None:
        message += f"   Відчувається як: `{format_and_escape(feels_like)}°C`\n"
    if humidity is not None:
        message += f"💧 Вологість: `{humidity}%`\n"
    if pressure_mmhg is not None:
        message += f"📊 Тиск: `{pressure_mmhg} мм рт\\. ст\\.`\n"
    if wind_speed is not None:
        message += f"💨 Вітер: `{format_and_escape(wind_speed)} м/с`\n"
    return message.strip()

async def get_weather_command(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles /weather command or weather button press.

    Args:
        update: Telegram update object.
        context: Telegram context.
    """
    if not update.message:
        logger.warning("get_weather_command called without update.message")
        return

    city = " ".join(context.args) if context.args else DEFAULT_CITY
    logger.info(f"Fetching weather for {city}")

    weather_data = get_weather(city)
    message = format_weather_message(weather_data)
    parse_mode = ParseMode.MARKDOWN_V2 if weather_data and weather_data.get('cod') == 200 else None

    try:
        await update.message.reply_text(message, parse_mode=parse_mode)
    except telegram.error.TelegramError as e:
        logger.error(f"Error sending weather message: {e}")
        plain_message = message.replace('\\.', '.').replace('\\*', '*').replace('\\`', '`')
        await update.message.reply_text(plain_message)