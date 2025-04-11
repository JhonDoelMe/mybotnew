import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv
from button_handlers import main_reply_markup, handle_module_buttons
from weather import show_weather_menu, get_weather, handle_city_change
from currency import show_currency_menu, get_exchange_rate
from air_raid import show_air_raid_menu, check_air_raid, toggle_notifications, select_region, handle_air_raid_input

# Загрузка переменных окружения из .env
load_dotenv()

# Настройка логирования
logging.basicConfig(
    filename='bot.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: CallbackContext):
    """Обработчик команды /start"""
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! Выберите раздел:",
        reply_markup=main_reply_markup
    )

async def handle_message(update: Update, context: CallbackContext):
    """Обработчик текстовых сообщений"""
    text = update.message.text
    current_module = context.user_data.get('current_module')

    # Главное меню
    if text == '🌤️ Погода' or text == 'Погода':
        context.user_data['current_module'] = 'weather'
        await show_weather_menu(update, context)
    elif text == '💵 Курс валют' or text == 'Курс валют':
        context.user_data['current_module'] = 'currency'
        await show_currency_menu(update, context)
    elif text == '🚨 Воздушная тревога' or text == 'Воздушная тревога':
        context.user_data['current_module'] = 'air_raid'
        await show_air_raid_menu(update, context)
    elif text == 'Новости ТЦК':
        await update.message.reply_text("Этот раздел временно отключен.", reply_markup=main_reply_markup)
    # Обработка подменю
    elif current_module:
        await handle_module_buttons(update, context)
    else:
        await update.message.reply_text("Выберите раздел:", reply_markup=main_reply_markup)

async def error_handler(update: Update, context: CallbackContext):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")
    try:
        await update.message.reply_text("Произошла ошибка. Попробуйте снова.", reply_markup=main_reply_markup)
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения об ошибке: {e}")

def main():
    """Запуск бота"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не найден в .env")
        return

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    logger.info("Бот запущен")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()