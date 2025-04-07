import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
import weather
import currency
import air_raid
import tcc_news

logger = logging.getLogger(__name__)

# Главное меню (добавлено определение)
main_keyboard = [['Погода'], ['Курс валют'], ['Воздушная тревога'], ['Новости ТЦК']]
main_reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)

async def handle_weather_buttons(update: Update, context: CallbackContext) -> None:
    try:
        text = update.message.text
        if text == 'Текущая погода':
            await weather.get_weather(update, context)
        elif text == 'Сменить город':
            await update.message.reply_text("Введите название города:")
            context.user_data['awaiting_city'] = True
        elif text == 'Вернуться в главное меню':
            await update.message.reply_text(
                "Возвращаемся в главное меню",
                reply_markup=main_reply_markup
            )
            context.user_data.clear()
        else:
            await update.message.reply_text("Не понимаю ваш запрос в разделе 'Погода'.")
    except Exception as e:
        logger.error(f"Weather button error: {e}")
        await update.message.reply_text("Ошибка обработки запроса.")

async def handle_currency_buttons(update: Update, context: CallbackContext) -> None:
    try:
        text = update.message.text
        if text in ('USD', 'EUR'):
            await currency.get_exchange_rate(update, context)
        elif text == 'Вернуться в главное меню':
            await update.message.reply_text(
                "Возвращаемся в главное меню",
                reply_markup=main_reply_markup
            )
            context.user_data.clear()
        else:
            await update.message.reply_text("Не понимаю ваш запрос в разделе 'Курс валют'.")
    except Exception as e:
        logger.error(f"Currency button error: {e}")
        await update.message.reply_text("Ошибка обработки запроса.")

async def handle_air_raid_buttons(update: Update, context: CallbackContext) -> None:
    try:
        text = update.message.text
        if text == 'Проверить текущую тревогу':
            await air_raid.check_air_raid(update, context)
        elif text == 'Вернуться в главное меню':
            await update.message.reply_text(
                "Возвращаемся в главное меню",
                reply_markup=main_reply_markup
            )
            context.user_data.clear()
        else:
            await update.message.reply_text("Не понимаю ваш запрос в разделе 'Воздушная тревога'.")
    except Exception as e:
        logger.error(f"Air raid button error: {e}")
        await update.message.reply_text("Ошибка обработки запроса.")

async def handle_tcc_news_buttons(update: Update, context: CallbackContext) -> None:
    try:
        text = update.message.text
        if text == 'Получить последние новости':
            await tcc_news.get_tcc_news(update, context)
        elif text == 'Вернуться в главное меню':
            await update.message.reply_text(
                "Возвращаемся в главное меню",
                reply_markup=main_reply_markup
            )
            context.user_data.clear()
        else:
            await update.message.reply_text("Не понимаю ваш запрос в разделе 'Новости ТЦК'.")
    except Exception as e:
        logger.error(f"TCC news button error: {e}")
        await update.message.reply_text("Ошибка обработки запроса.")

async def handle_module_buttons(update: Update, context: CallbackContext) -> None:
    """Главный обработчик кнопок всех модулей"""
    try:
        current_module = context.user_data.get('current_module')
        
        if current_module == 'weather':
            await handle_weather_buttons(update, context)
        elif current_module == 'currency':
            await handle_currency_buttons(update, context)
        elif current_module == 'air_raid':
            await handle_air_raid_buttons(update, context)
        elif current_module == 'tcc_news':
            await handle_tcc_news_buttons(update, context)
        else:
            await update.message.reply_text("Ошибка: неизвестный модуль")
            await update.message.reply_text(
                "Возвращаемся в главное меню",
                reply_markup=main_reply_markup
            )
            context.user_data.clear()
    except Exception as e:
        logger.error(f"Module buttons error: {e}")
        await update.message.reply_text("Произошла ошибка при обработке команды")
        await update.message.reply_text(
            "Возвращаемся в главное меню",
            reply_markup=main_reply_markup
        )
        context.user_data.clear()