from telegram import Update
from telegram.ext import CallbackContext
import weather
import currency
import air_raid
import tcc_news
import logging

logger = logging.getLogger(__name__)

async def handle_weather_buttons(update: Update, context: CallbackContext) -> None:
    try:
        text = update.message.text
        if text == 'Текущая погода':
            await weather.get_weather(update, context)
        elif text != 'Вернуться в главное меню':
            await update.message.reply_text("Не понимаю ваш запрос в разделе 'Погода'.")
    except Exception as e:
        logger.error(f"Weather button error: {e}")
        await update.message.reply_text("Ошибка обработки запроса.")

async def handle_currency_buttons(update: Update, context: CallbackContext) -> None:
    try:
        text = update.message.text
        if text in ('USD', 'EUR'):
            await currency.get_exchange_rate(update, context)
        elif text != 'Вернуться в главное меню':
            await update.message.reply_text("Не понимаю ваш запрос в разделе 'Курс валют'.")
    except Exception as e:
        logger.error(f"Currency button error: {e}")
        await update.message.reply_text("Ошибка обработки запроса.")

async def handle_air_raid_buttons(update: Update, context: CallbackContext) -> None:
    try:
        text = update.message.text
        if text == 'Проверить текущую тревогу':
            await air_raid.check_air_raid(update, context)
        elif text != 'Вернуться в главное меню':
            await update.message.reply_text("Не понимаю ваш запрос в разделе 'Воздушная тревога'.")
    except Exception as e:
        logger.error(f"Air raid button error: {e}")
        await update.message.reply_text("Ошибка обработки запроса.")

async def handle_tcc_news_buttons(update: Update, context: CallbackContext) -> None:
    try:
        text = update.message.text
        if text == 'Получить последние новости':
            await tcc_news.get_tcc_news(update, context)
        elif text != 'Вернуться в главное меню':
            await update.message.reply_text("Не понимаю ваш запрос в разделе 'Новости ТЦК'.")
    except Exception as e:
        logger.error(f"TCC news button error: {e}")
        await update.message.reply_text("Ошибка обработки запроса.")