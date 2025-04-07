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
)

# Импортируем функции из модулей
import weather
import currency
import air_raid
import tcc_news
import database
import button_handlers

# Настраиваем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения из .env
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
        logger.error(f"Ошибка при обработке команды /start: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")

# Обработка главного меню
async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    user = update.effective_user
    logger.info(f"Пользователь {user.id} ({user.username}) нажал кнопку главного меню: {text}")
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
        logger.error(f"Ошибка при обработке главного меню ({text}) от пользователя {user.id}: {e}")
        await update.message.reply_text("Произошла ошибка при обработке запроса. Попробуйте позже.")

# Обработка кнопок внутри модулей
async def handle_module_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    user = update.effective_user
    current_module = context.user_data.get('current_module')

    logger.info(f"Пользователь {user.id} ({user.username}) нажал кнопку '{text}' в модуле '{current_module}'")

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
        logger.error(f"Ошибка при обработке кнопки '{text}' в модуле '{current_module}' от пользователя {user.id}: {e}")
        await update.message.reply_text("Произошла ошибка при обработке запроса. Попробуйте позже.")

# Обработчик ошибок
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Произошла ошибка при обработке обновления: {context.error}")

# Универсальный роутер сообщений
async def route_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_module = context.user_data.get('current_module')
    if current_module:
        await handle_module_buttons(update, context)
    else:
        await handle_main_menu(update, context)

# Главная функция запуска
def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.critical("Ошибка: не найден TELEGRAM_BOT_TOKEN в .env")
        return

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).timezone(pytz.utc).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_messages))
    app.add_error_handler(error_handler)

    logger.info("Бот запущен.")
    app.run_polling()

if __name__ == "__main__":
    main()
