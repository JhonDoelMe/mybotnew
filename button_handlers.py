# button_handlers.py
from telegram import Update
from telegram.ext import CallbackContext
import weather

def handle_weather_buttons(update: Update, context: CallbackContext) -> None:
    """Обрабатывает нажатия кнопок в модуле погоды."""
    text = update.message.text
    if text == 'Текущая погода':
        weather.get_weather(update, context)
    elif text == 'Вернуться в главное меню':
        # Обработка возврата в главное меню уже есть в main.py
        pass
    else:
        update.message.reply_text("Не понимаю ваш запрос в разделе 'Погода'.")

def handle_currency_buttons(update: Update, context: CallbackContext) -> None:
    """Обрабатывает нажатия кнопок в модуле курса валют."""
    text = update.message.text
    if text == 'Вернуться в главное меню':
        pass # Обработка в main.py
    else:
        update.message.reply_text("Функционал раздела 'Курс валют' пока не реализован.")

def handle_air_raid_buttons(update: Update, context: CallbackContext) -> None:
    """Обрабатывает нажатия кнопок в модуле воздушной тревоги."""
    text = update.message.text
    if text == 'Вернуться в главное меню':
        pass # Обработка в main.py
    else:
        update.message.reply_text("Функционал раздела 'Воздушная тревога' пока не реализован.")

def handle_tcc_news_buttons(update: Update, context: CallbackContext) -> None:
    """Обрабатывает нажатия кнопок в модуле новостей ТЦК."""
    text = update.message.text
    if text == 'Вернуться в главное меню':
        pass # Обработка в main.py
    else:
        update.message.reply_text("Функционал раздела 'Новости ТЦК' пока не реализован.")