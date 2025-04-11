from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Главное меню
main_keyboard = [
    ['🌤️ Погода', '💵 Курс валют'],
    ['🚨 Воздушная тревога']
]
main_reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)

class ButtonHandler:
    @staticmethod
    async def handle_main_menu(update: Update, context: CallbackContext):
        """Обработка главного меню"""
        text = update.message.text.lower()
        
        if any(word in text for word in ['погода', '🌤️']):
            context.user_data['current_module'] = 'weather'
            await weather.show_weather_menu(update, context)
        elif any(word in text for word in ['курс', 'валюта', '💵']):
            context.user_data['current_module'] = 'currency'
            await currency.show_currency_menu(update, context)
        elif any(word in text for word in ['тревога', '🚨']):
            context.user_data['current_module'] = 'air_raid'
            await air_raid.show_air_raid_menu(update, context)
        else:
            await update.message.reply_text(
                "Выберите раздел:",
                reply_markup=main_reply_markup
            )

    @staticmethod
    async def handle_weather_buttons(update: Update, context: CallbackContext):
        """Обработчик кнопок погоды"""
        try:
            text = update.message.text
            
            if text == '🌞 Текущая погода':
                await weather.get_weather(update, context)
            elif text == '🏙️ Изменить город':
                await weather.handle_city_change(update, context)
            elif text == '⬅️ Главное меню':
                await ButtonHandler.return_to_main_menu(update, context)
                
        except Exception as e:
            logger.error(f"Ошибка обработки погоды: {e}")
            await update.message.reply_text(
                "⚠️ Ошибка обработки запроса",
                reply_markup=main_reply_markup
            )

    @staticmethod
    async def handle_currency_buttons(update: Update, context: CallbackContext):
        """Обработчик кнопок валют"""
        try:
            text = update.message.text
            
            if text in ('💲 USD', '€ EUR'):
                await currency.get_exchange_rate(update, context)
            elif text == '🔄 Изменить валюту':
                await currency.show_currency_menu(update, context)
            elif text == '⬅️ Главное меню':
                await ButtonHandler.return_to_main_menu(update, context)
                
        except Exception as e:
            logger.error(f"Ошибка обработки валют: {e}")
            await update.message.reply_text(
                "⚠️ Ошибка обработки запроса",
                reply_markup=main_reply_markup
            )

    @staticmethod
    async def handle_air_raid_buttons(update: Update, context: CallbackContext):
        """Обработчик кнопок тревог"""
        try:
            text = update.message.text
            
            if text == '🔍 Проверить тревоги':
                await air_raid.check_air_raid(update, context)
            elif text == '🌍 Выбрать регион':
                await air_raid.select_region(update, context)
            elif text in ('🔔 Вкл уведомления', '🔕 Выкл уведомления'):
                await air_raid.toggle_notifications(update, context)
            elif text == '⬅️ Главное меню':
                await ButtonHandler.return_to_main_menu(update, context)
            elif context.user_data.get('awaiting_region'):
                await air_raid.handle_region_selection(update, context)
                
        except Exception as e:
            logger.error(f"Ошибка обработки тревог: {e}")
            await update.message.reply_text(
                "⚠️ Ошибка обработки запроса",
                reply_markup=main_reply_markup
            )

    @staticmethod
    async def return_to_main_menu(update: Update, context: CallbackContext):
        """Вернуться в главное меню"""
        context.user_data.clear()
        await update.message.reply_text(
            "Главное меню",
            reply_markup=main_reply_markup
        )

async def handle_module_buttons(update: Update, context: CallbackContext):
    """Главный обработчик кнопок модулей"""
    current_module = context.user_data.get('current_module')
    
    if not current_module:
        await ButtonHandler.handle_main_menu(update, context)
        return
    
    try:
        if current_module == 'weather':
            await ButtonHandler.handle_weather_buttons(update, context)
        elif current_module == 'currency':
            await ButtonHandler.handle_currency_buttons(update, context)
        elif current_module == 'air_raid':
            await ButtonHandler.handle_air_raid_buttons(update, context)
            
    except Exception as e:
        logger.error(f"Ошибка обработки модуля: {e}")
        await ButtonHandler.return_to_main_menu(update, context)