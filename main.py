import os
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Импорт модулей
import weather
import currency
import air_raid
import tcc_news
import button_handlers
from database import setup_database

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Загрузка конфигурации
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Главное меню
main_keyboard = [['Погода'], ['Курс валют'], ['Воздушная тревога'], ['Новости ТЦК']]
main_reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"User {user.id} started bot")
    context.user_data.clear()
    try:
        await update.message.reply_markdown_v2(
            fr"Привет\, {user.mention_markdown_v2()}\! 👋\n\nВыберите раздел\:",
            reply_markup=main_reply_markup,
        )
    except Exception as e:
        logger.error(f"Start error: {e}")
        await update.message.reply_text("Ошибка запуска бота")

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    user = update.effective_user
    logger.info(f"User {user.id} selected {text}")
    
    try:
        if text == 'Погода':
            await weather.show_weather_menu(update, context)
            context.user_data['current_module'] = 'weather'
        elif text == 'Курс валют':
            await currency.show_currency_menu(update, context)
            context.user_data['current_module'] = 'currency'
        elif text == 'Воздушная тревога':
            await air_raid.show_air_raid_menu(update, context)
            context.user_data['current_module'] = 'air_raid'
        elif text == 'Новости ТЦК':
            await tcc_news.show_tcc_news_menu(update, context)
            context.user_data['current_module'] = 'tcc_news'
        else:
            await update.message.reply_text("Неизвестная команда")
    except Exception as e:
        logger.error(f"Menu error: {e}")
        await update.message.reply_text("Ошибка обработки команды")

async def route_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'current_module' in context.user_data:
        await button_handlers.handle_module_buttons(update, context)
    else:
        await handle_main_menu(update, context)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error: {context.error}")

def create_application():
    """Фабрика приложения бота"""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set")
    
    app = ApplicationBuilder()\
        .token(TELEGRAM_BOT_TOKEN)\
        .post_init(setup_database)\
        .build()

    # Регистрация обработчиков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_messages))
    app.add_error_handler(error_handler)
    
    return app

def main():
    try:
        app = create_application()
        logger.info("Бот запущен")
        app.run_polling()
    except Exception as e:
        logger.critical(f"Bot failed: {e}")

if __name__ == "__main__":
    main()