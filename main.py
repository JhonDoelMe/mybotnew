import os
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    ConversationHandler
)
from dotenv import load_dotenv
from button_handlers import main_reply_markup, handle_module_buttons
from weather import (
    show_weather_menu,
    get_weather,
    handle_city_change,
    handle_city_input
)
from currency import show_currency_menu, get_exchange_rate, handle_currency_change
from air_raid import (
    show_air_raid_menu,
    check_air_raid,
    toggle_notifications,
    select_region,
    handle_region_selection
)
from database import init_db

# Состояния для ConversationHandler
WEATHER_CITY, CURRENCY_SELECTION, AIR_RAID_REGION = range(3)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: CallbackContext):
    """Обработчик команды /start"""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n"
        "Я помогу вам с информацией о:\n"
        "- 🌤️ Погоде\n"
        "- 💵 Курсах валют\n"
        "- 🚨 Воздушных тревогах\n\n"
        "Выберите раздел:",
        reply_markup=main_reply_markup
    )

async def handle_message(update: Update, context: CallbackContext):
    """Главный обработчик текстовых сообщений"""
    try:
        text = update.message.text
        
        # Проверка на ожидание ввода данных
        if context.user_data.get('awaiting_city'):
            await handle_city_input(update, context)
            return
        elif context.user_data.get('awaiting_region'):
            await handle_region_selection(update, context)
            return
        
        # Обработка главного меню
        if text in ['🌤️ Погода', '💵 Курс валют', '🚨 Воздушная тревога']:
            await handle_module_selection(update, context)
        else:
            await handle_module_buttons(update, context)
            
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка. Попробуйте снова.",
            reply_markup=main_reply_markup
        )

async def handle_module_selection(update: Update, context: CallbackContext):
    """Обработка выбора модуля"""
    text = update.message.text
    
    if text == '🌤️ Погода':
        context.user_data['current_module'] = 'weather'
        await show_weather_menu(update, context)
    elif text == '💵 Курс валют':
        context.user_data['current_module'] = 'currency'
        await show_currency_menu(update, context)
    elif text == '🚨 Воздушная тревога':
        context.user_data['current_module'] = 'air_raid'
        await show_air_raid_menu(update, context)

async def error_handler(update: Update, context: CallbackContext):
    """Глобальный обработчик ошибок"""
    logger.error(msg="Ошибка в обработчике:", exc_info=context.error)
    
    if update and update.message:
        await update.message.reply_text(
            "⚠️ Произошла непредвиденная ошибка. Мы уже работаем над ее устранением.",
            reply_markup=main_reply_markup
        )

def setup_handlers(application):
    """Настройка обработчиков команд и сообщений"""
    # Обработчик команды /start
    application.add_handler(CommandHandler("start", start))
    
    # ConversationHandler для погоды
    weather_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r'^(🌤️ Погода|Погода)$'), handle_module_selection)],
        states={
            WEATHER_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city_input)]
        },
        fallbacks=[CommandHandler("start", start)],
        map_to_parent={
            ConversationHandler.END: ConversationHandler.END
        }
    )
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)

def main():
    """Запуск бота"""
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден в .env")
        return
    
    # Инициализация базы данных
    init_db()
    
    # Создание и настройка приложения
    application = Application.builder().token(token).build()
    
    # Настройка обработчиков
    setup_handlers(application)
    
    # Запуск бота
    logger.info("🤖 Бот запущен")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}")