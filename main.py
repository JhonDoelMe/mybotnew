# main.py

import os
import logging
import pytz
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    JobQueue,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Импорт модулей (предполагается, что они у тебя есть в проекте)
import weather
import currency
import air_raid
import tcc_news
import database
import button_handlers

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка токена
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Главное меню
main_keyboard = [['Погода'], ['Курс валют'], ['Воздушная тревога'], ['Новости ТЦК']]
main_reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"Пользователь {user.id} ({user.username}) запустил бота.")
    context.user_data.clear()
    try:
        await update.message.reply_markdown_v2(
            fr"Привет, {user.mention_markdown_v2()}! 👋\n\nВыберите интересующий вас раздел:",
            reply_markup=main_reply_markup,
        )
    except Exception as e:
        logger.error(f"Ошибка при /start: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")

# Обработка главного меню
async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    user = update.effective_user
    logger.info(f"Пользователь {user.id} выбрал {text} в главном меню.")
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
            await update.message.reply_text("Не понимаю ваш запрос.")
    except Exception as e:
        logger.error(f"Ошибка в главном меню: {e}")
        await update.message.reply_text("Произошла ошибка при обработке запроса.")

# Обработка кнопок модулей
async def handle_module_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    user = update.effective_user
    current_module = context.user_data.get('current_module')
    logger.info(f"Пользователь {user.id} нажал '{text}' в модуле '{current_module}'")

    try:
        if text == 'Вернуться в главное меню':
            await start(update, context)
            context.user_data.pop('current_module', None)
            return

        if current_module == 'weather':
            await button_handlers.handle_weather_buttons(update, context)
        elif current_module == 'currency':
            await button_handlers.handle_currency_buttons(update, context)
        elif current_module == 'air_raid':
            await button_handlers.handle_air_raid_buttons(update, context)
        elif current_module == 'tcc_news':
            await button_handlers.handle_tcc_news_buttons(update, context)
        else:
            await update.message.reply_text("Не понимаю ваш запрос в этом разделе.")
    except Exception as e:
        logger.error(f"Ошибка при нажатии кнопки: {e}")
        await update.message.reply_text("Произошла ошибка при обработке запроса.")

# Универсальный роутер
async def route_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_module = context.user_data.get('current_module')
    if current_module:
        await handle_module_buttons(update, context)
    else:
        await handle_main_menu(update, context)

# Обработка ошибок
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Ошибка во время обработки обновления: {context.error}")

# Главная функция
def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.critical("Ошибка: TELEGRAM_BOT_TOKEN не найден в .env")
        return

    # Инициализация планировщика с pytz
    scheduler = AsyncIOScheduler(timezone=pytz.utc)
    job_queue = JobQueue(scheduler=scheduler)

    # Сборка приложения
    app = ApplicationBuilder()\
        .token(TELEGRAM_BOT_TOKEN)\
        .job_queue(job_queue)\
        .build()

    # Обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_messages))
    app.add_error_handler(error_handler)

    logger.info("Бот успешно запущен.")
    app.run_polling()

# Запуск
if __name__ == "__main__":
    main()
    