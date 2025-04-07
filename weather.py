# weather.py
import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import CallbackContext

load_dotenv()
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
BASE_URL = "http://api.openweathermap.org/data/2.5/weather?"

def get_weather(update: Update, context: CallbackContext) -> None:
    """Получает и отправляет информацию о погоде."""
    city = "Samar,UA"  # Пока что зададим город по умолчанию
    params = {
        "q": city,
        "appid": OPENWEATHERMAP_API_KEY,
        "units": "metric",  # Градусы Цельсия
        "lang": "ru"
    }

    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()  # Проверка на ошибки HTTP
        weather_data = response.json()

        if weather_data["cod"] == 200:
            weather_description = weather_data["weather"][0]["description"]
            temperature = weather_data["main"]["temp"]
            humidity = weather_data["main"]["humidity"]
            wind_speed = weather_data["wind"]["speed"]

            weather_emoji = get_weather_emoji(weather_description)

            message = f"Погода в городе {weather_data['name']} {weather_emoji}\n"
            message += f"Описание: {weather_description.capitalize()}\n"
            message += f"Температура: {temperature}°C\n"
            message += f"Влажность: {humidity}%\n"
            message += f"Ветер: {wind_speed} м/с"

            update.message.reply_text(message)
        else:
            update.message.reply_text(f"Произошла ошибка при получении погоды: {weather_data['message']}")

    except requests.exceptions.RequestException as e:
        update.message.reply_text(f"Ошибка при запросе к API погоды: {e}")
    except KeyError:
        update.message.reply_text("Не удалось обработать данные о погоде. Попробуйте позже.")
    except Exception as e:
        update.message.reply_text(f"Произошла непредвиденная ошибка: {e}")

def get_weather_emoji(description: str) -> str:
    """Возвращает эмодзи в зависимости от описания погоды."""
    description = description.lower()
    if "ясно" in description:
        return "☀️"
    elif "облачно" in description:
        return "☁️"
    elif "дождь" in description or "ливень" in description:
        return "🌧️"
    elif "снег" in description:
        return "❄️"
    elif "гроза" in description:
        return "⛈️"
    elif "туман" in description:
        return "🌫️"
    else:
        return "❓"