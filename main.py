# main.py
import os
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Импортируем функции из наших модулей
import weather
import currency
import air_raid
import tcc_news
import database  # Пока не используется, но будет нужен

# Настраиваем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения из файла .env
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Клавиатура главного меню
main_keyboard = [['Погода'], ['Курс валют'], ['Воздушная тревога'], ['Новости ТЦК']]
reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)

def start(update: Update, context: CallbackContext) -> None:
    """Отправляет приветственное сообщение и главное меню."""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} ({user.username}) запустил бота.")
    try:
        update.message.reply_markdown_v2(
            fr"Привет, {user.mention_markdown_v2()}! 👋\n\nВыберите интересующий вас раздел:",
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /start: {e}")
        update.message.reply_text("Произошла ошибка. Попробуйте позже.")

def handle_menu(update: Update, context: CallbackContext) -> None:
    """Обрабатывает нажатия кнопок главного меню."""
    text = update.message.text
    user = update.effective_user
    logger.info(f"Пользователь {user.id} ({user.username}) нажал кнопку: {text}")
    try:
        if text == 'Погода':
            weather.get_weather(update, context)
        elif text == 'Курс валют':
            currency.get_exchange_rate(update, context)
        elif text == 'Воздушная тревога':
            air_raid.check_air_raid(update, context)
        elif text == 'Новости ТЦК':
            tcc_news.get_tcc_news(update, context)
        else:
            update.message.reply_text("Не понимаю ваш запрос.")
    except Exception as e:
        logger.error(f"Ошибка при обработке меню ({text}) от пользователя {user.id}: {e}")
        update.message.reply_text("Произошла ошибка при обработке запроса. Попробуйте позже.")

def error_handler(update: Update, context: CallbackContext) -> None:
    """Обработчик ошибок, вызванных обновлениями."""
    logger.error(f"Произошла ошибка при обработке обновления:\n{context.error}")
    # Вы можете добавить здесь дополнительную логику, например, отправку уведомления администратору бота

def main():
    """Запускает бота."""
    if not TELEGRAM_BOT_TOKEN:
        print("Ошибка: Не найден TELEGRAM_BOT_TOKEN в файле .env")
        return

    # Создаем Updater и передаем ему токен вашего бота
    updater = Updater(TELEGRAM_BOT_TOKEN)

    # Получаем диспетчера для регистрации обработчиков
    dispatcher = updater.dispatcher

    # Обработчик команды /start
    dispatcher.add_handler(CommandHandler("start", start))

    # Обработчик текстовых сообщений (для кнопок меню)
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_menu))

    # Обработчик ошибок
    dispatcher.add_error_handler(error_handler)

    # Запускаем бота
    updater.start_polling()

    # Бот будет работать до тех пор, пока вы не нажмете Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main()