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
from database import get_connection, get_or_create_user, setup_database

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    with get_connection() as conn:
        get_or_create_user(conn, {
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'language_code': user.language_code
        })
    
    context.user_data.clear()
    await update.message.reply_text(
        f"Привет, {user.first_name}! Выберите раздел:",
        reply_markup=main_reply_markup
    )

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка главного меню"""
    text = update.message.text
    user_id = update.effective_user.id
    
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
    except Exception as e:
        logger.error(f"Menu error: {e}")
        await update.message.reply_text("Ошибка обработки команды")

async def route_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Маршрутизатор сообщений"""
    user_id = update.effective_user.id
    
    # Проверка регистрации пользователя
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            await start(update, context)
            return
    
    if 'awaiting_city' in context.user_data:
        await weather.handle_city_change(update, context)
    elif 'current_module' in context.user_data:
        await button_handlers.handle_module_buttons(update, context)
    else:
        await handle_main_menu(update, context)

async def post_init(application):
    """Инициализация при запуске"""
    setup_database()
    logger.info("Database initialized")

def create_application():
    """Создание приложения бота"""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set")
    
    app = ApplicationBuilder()\
        .token(TELEGRAM_BOT_TOKEN)\
        .post_init(post_init)\
        .build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_messages))
    
    return app

def main():
    """Точка входа"""
    try:
        app = create_application()
        logger.info("Bot started")
        app.run_polling()
    except Exception as e:
        logger.critical(f"Bot failed: {e}")

if __name__ == "__main__":
    main()