# weather.py
import requests
import json
import logging
from typing import Optional, Dict, Any

import telegram # Добавлено для telegram.helpers
from telegram import helpers # Добавлено для telegram.helpers
from telegram.ext import ContextTypes
from telegram.constants import ParseMode # Добавлено для ParseMode

import config # Импортируем модуль config
from constants import DEFAULT_CITY

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# URL API OpenWeatherMap
WEATHER_API_URL = "http://api.openweathermap.org/data/2.5/weather"

def get_weather(city: str) -> Optional[Dict[str, Any]]:
    """
    Получает данные о погоде для указанного города с OpenWeatherMap API.

    Args:
        city: Название города.

    Returns:
        Optional[Dict[str, Any]]: Словарь с данными о погоде или None в случае ошибки.
    """
    api_key = config.cfg.get('WEATHER_API_KEY')
    if not api_key:
        logger.error("Weather API key (WEATHER_API_KEY) not configured.")
        return None

    params = {
        'q': city,
        'appid': api_key,
        'units': 'metric', # Градусы Цельсия
        'lang': 'uk' # Язык ответа - украинский
    }

    try:
        response = requests.get(WEATHER_API_URL, params=params, timeout=10)
        response.raise_for_status() # Проверка на HTTP ошибки (кроме 404, обрабатываем отдельно)

        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, dict):
                    return data
                else:
                    logger.error(f"Weather API returned unexpected data type: {type(data)}. Expected dict.")
                    return None
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON response from Weather API: {e}")
                logger.debug(f"Response text: {response.text}")
                return None
            except Exception as e:
                 logger.error(f"An unexpected error occurred during JSON processing: {e}")
                 return None
        else:
            # Эта ветка скорее всего не выполнится из-за raise_for_status, но для полноты
            logger.error(f"Weather API request failed with status code {response.status_code}: {response.text}")
            return None

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"City '{city}' not found by Weather API.")
            return {'cod': '404', 'message': 'city not found'}
        elif e.response.status_code == 401:
            logger.error(f"Weather API request failed: Invalid API key or not authorized. {e}")
            return None
        else:
             logger.error(f"HTTP error fetching weather for {city}: {e}")
             return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error fetching weather for {city}: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred in get_weather for {city}: {e}")
        return None


def format_weather_message(weather_data: Dict[str, Any]) -> str:
    """
    Форматирует сообщение с данными о погоде для ParseMode.MARKDOWN_V2.

    Args:
        weather_data: Словарь с данными от API OpenWeatherMap.

    Returns:
        str: Отформатированное сообщение для пользователя.
    """
    if not weather_data or weather_data.get('cod') != 200:
        if weather_data and weather_data.get('cod') == '404':
            # Точка не требует экранирования, т.к. не используем Markdown V2 для этого сообщения
            return "На жаль, не можу знайти інформацію для такого міста. Спробуйте іншу назву."
        # Точка не требует экранирования
        return "Вибачте, не вдалося отримати дані про погоду."

    # Используем хелпер для экранирования имени города (на всякий случай)
    city_name = helpers.escape_markdown(weather_data.get('name', 'Невідоме місто'), version=2)
    main_info = weather_data.get('main', {})
    weather_desc_list = weather_data.get('weather', [])
    wind_info = weather_data.get('wind', {})

    temp = main_info.get('temp')
    feels_like = main_info.get('feels_like')
    humidity = main_info.get('humidity')
    pressure_hpa = main_info.get('pressure')
    wind_speed = wind_info.get('speed')

    # Экранируем описание погоды
    description = helpers.escape_markdown(
        weather_desc_list[0].get('description', 'невідомо') if weather_desc_list else 'невідомо',
        version=2
    )
    icon_code = weather_desc_list[0].get('icon', '') if weather_desc_list else ''

    weather_icons = {
        "01d": "☀️", "01n": "🌙", "02d": "⛅️", "02n": "☁️", "03d": "☁️", "03n": "☁️",
        "04d": "☁️", "04n": "☁️", "09d": "🌦", "09n": "🌧", "10d": "🌧", "10n": "🌧",
        "11d": "⛈", "11n": "⛈", "13d": "❄️", "13n": "❄️", "50d": "🌫", "50n": "🌫",
    }
    weather_emoji = weather_icons.get(icon_code, "")

    pressure_mmhg = int(pressure_hpa * 0.750062) if pressure_hpa is not None else None

    # --- Формирование сообщения с экранированием ---
    # Функция для форматирования и экранирования чисел
    def format_and_escape(value: Optional[float], precision: int = 1) -> str:
        if value is None:
            return "N/A"
        # Форматируем с нужной точностью, заменяем '.' на '\.'
        return f"{value:.{precision}f}".replace('.', '\\.')

    message = f"*Погода в місті* {city_name}:\n\n"
    message += f"{weather_emoji} {description.capitalize()}\n"
    if temp is not None:
        message += f"🌡 Температура: `{format_and_escape(temp)}°C`\n"
    if feels_like is not None:
        message += f"   Відчувається як: `{format_and_escape(feels_like)}°C`\n"
    if humidity is not None:
        # Для целых чисел точка не нужна
        message += f"💧 Вологість: `{humidity}%`\n"
    if pressure_mmhg is not None:
        # Для целых чисел точка не нужна
        message += f"📊 Тиск: `{pressure_mmhg} мм рт\\. ст\\.`\n" # Экранируем точки в "мм рт. ст."
    if wind_speed is not None:
        message += f"💨 Вітер: `{format_and_escape(wind_speed)} м/с`\n"

    return message.strip()


async def get_weather_command(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /weather или текстового запроса погоды.
    Спрашивает город, если он не передан в аргументах.
    """
    if not update.message:
        logger.warning("get_weather_command called without update.message")
        return

    city = " ".join(context.args) if context.args else None

    if not city:
        city = DEFAULT_CITY
        logger.info(f"City not provided, using default: {city}")
        # Можно добавить сообщение с просьбой указать город, если нужно
        # plain_text_request = f"Показую погоду для {city}. Щоб дізнатись погоду для іншого міста, напишіть '/weather Назва міста'"
        # await update.message.reply_text(plain_text_request)


    if city:
        weather_data = get_weather(city)
        # Форматируем сообщение (уже готово для MarkdownV2)
        message = format_weather_message(weather_data)

        # Определяем parse_mode в зависимости от того, удалось ли получить данные
        parse_mode = None
        if weather_data and weather_data.get('cod') == 200:
            parse_mode = ParseMode.MARKDOWN_V2

        try:
            await update.message.reply_text(message, parse_mode=parse_mode)
        except telegram.error.TelegramError as e:
            logger.error(f"Error sending weather message (parse_mode={parse_mode}): {e}")
            # Попытка отправить без форматирования в случае ошибки с MarkdownV2
            if parse_mode == ParseMode.MARKDOWN_V2:
                try:
                    # Упрощенная версия без экранирования
                    plain_message = message.replace('\\.', '.')\
                                           .replace('\\*', '*')\
                                           .replace('\\`', '`') # и т.д. или переформатировать заново
                    # Проще переформатировать заново без Markdown
                    plain_message = format_weather_message_plain(weather_data) # Нужна отдельная функция
                    await update.message.reply_text(plain_message)
                    logger.info("Sent weather message without markdown due to previous error.")
                except telegram.error.TelegramError as final_e:
                    logger.error(f"Failed to send weather message even without markdown: {final_e}")
                    await update.message.reply_text("Вибачте, сталася помилка при відправці погоди.") # Общее сообщение об ошибке
            else:
                 # Если ошибка была даже без форматирования
                 await update.message.reply_text("Вибачте, сталася помилка при відправці погоди.")

# Дополнительная функция для простого текста (если нужна)
def format_weather_message_plain(weather_data: Dict[str, Any]) -> str:
    """Форматирует сообщение о погоде как обычный текст."""
    if not weather_data or weather_data.get('cod') != 200:
        if weather_data and weather_data.get('cod') == '404':
            return "На жаль, не можу знайти інформацію для такого міста. Спробуйте іншу назву."
        return "Вибачте, не вдалося отримати дані про погоду."

    city_name = weather_data.get('name', 'Невідоме місто')
    main_info = weather_data.get('main', {})
    weather_desc_list = weather_data.get('weather', [])
    wind_info = weather_data.get('wind', {})

    temp = main_info.get('temp')
    feels_like = main_info.get('feels_like')
    humidity = main_info.get('humidity')
    pressure_hpa = main_info.get('pressure')
    wind_speed = wind_info.get('speed')

    description = weather_desc_list[0].get('description', 'невідомо') if weather_desc_list else 'невідомо'
    icon_code = weather_desc_list[0].get('icon', '') if weather_desc_list else ''

    weather_icons = {"01d": "☀️", "01n": "🌙", "02d": "⛅️", "02n": "☁️", "03d": "☁️", "03n": "☁️", "04d": "☁️", "04n": "☁️", "09d": "🌦", "09n": "🌧", "10d": "🌧", "10n": "🌧", "11d": "⛈", "11n": "⛈", "13d": "❄️", "13n": "❄️", "50d": "🌫", "50n": "🌫"}
    weather_emoji = weather_icons.get(icon_code, "")
    pressure_mmhg = int(pressure_hpa * 0.750062) if pressure_hpa is not None else None

    message = f"Погода в місті {city_name}:\n\n"
    message += f"{weather_emoji} {description.capitalize()}\n"
    if temp is not None: message += f"🌡 Температура: {temp:.1f}°C\n"
    if feels_like is not None: message += f"   Відчувається як: {feels_like:.1f}°C\n"
    if humidity is not None: message += f"💧 Вологість: {humidity}%\n"
    if pressure_mmhg is not None: message += f"📊 Тиск: {pressure_mmhg} мм рт. ст.\n"
    if wind_speed is not None: message += f"💨 Вітер: {wind_speed:.1f} м/с\n"

    return message.strip()