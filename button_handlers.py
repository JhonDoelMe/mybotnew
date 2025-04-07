from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
import weather
import currency
import air_raid
import logging

logger = logging.getLogger(__name__)

# Главное меню с эмодзи
main_keyboard = [['🌤️ Погода'], ['💵 Курс валют'], ['🚨 Воздушная тревога']]
main_reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)

async def handle_weather_buttons(update: Update, context: CallbackContext):
    """Обработчик кнопок погоды"""
    try:
        text = update.message.text
        if text == '🌞 Текущая погода':
            await weather.get_weather(update, context)
        elif text == '🏙️ Изменить город':
            await weather.handle_city_change(update, context)
        elif text == '⬅️ Вернуться в главное меню':
            await update.message.reply_text("Главное меню", reply_markup=main_reply_markup)
            context.user_data.clear()
    except Exception as e:
        logger.error(f"Weather button error: {e}")
        await update.message.reply_text("Ошибка обработки запроса")

async def handle_currency_buttons(update: Update, context: CallbackContext):
    """Обработчик кнопок валют"""
    try:
        text = update.message.text
        if text in ('💲 USD', '€ EUR'):
            await currency.get_exchange_rate(update, context)
        elif text == '🔄 Изменить валюту':
            await currency.show_currency_menu(update, context)
        elif text == '⬅️ Вернуться в главное меню':
            await update.message.reply_text("Главное меню", reply_markup=main_reply_markup)
            context.user_data.clear()
    except Exception as e:
        logger.error(f"Currency button error: {e}")
        await update.message.reply_text("Ошибка обработки запроса")

async def handle_air_raid_buttons(update: Update, context: CallbackContext):
    """Обработчик кнопок тревог"""
    try:
        text = update.message.text
        if text == '🔍 Проверить тревоги':
            await air_raid.check_air_raid(update, context)
        elif text in ('🔔 Включить уведомления', '🔕 Отключить уведомления'):
            await air_raid.toggle_notifications(update, context)
        elif text == '🌍 Выбрать область':
            await air_raid.select_oblast(update, context)
        elif text == '🏘️ Выбрать город':
            await air_raid.select_location(update, context)
        elif text == '⬅️ Вернуться в главное меню':
            await update.message.reply_text("Главное меню", reply_markup=main_reply_markup)
            context.user_data.clear()
        else:
            await air_raid.handle_air_raid_input(update, context)
    except Exception as e:
        logger.error(f"Air raid button error: {e}")
        await update.message.reply_text("Ошибка обработки запроса")

async def handle_module_buttons(update: Update, context: CallbackContext):
    """Главный обработчик кнопок модулей"""
    try:
        current_module = context.user_data.get('current_module')
        if not current_module:
            await update.message.reply_text("Выберите раздел", reply_markup=main_reply_markup)
            return
        
        if current_module == 'weather':
            await handle_weather_buttons(update, context)
        elif current_module == 'currency':
            await handle_currency_buttons(update, context)
        elif current_module == 'air_raid':
            await handle_air_raid_buttons(update, context)
    except Exception as e:
        logger.error(f"Module buttons error: {e}")
        await update.message.reply_text("Ошибка обработки команды")
        await update.message.reply_text("Главное меню", reply_markup=main_reply_markup)
        context.user_data.clear()