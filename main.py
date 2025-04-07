# main.py
import os
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, filters

# Импортируем функции из наших модулей
import weather
import currency
import air_raid
import tcc_news
import database  # Пока не используется, но будет нужен
import button_handlers  # Создадим этот файл позже

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
main_reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)

def start(update: Update, context: CallbackContext) -> None:
    """Отправляет приветственное сообщение и главное меню."""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} ({user.username}) запустил бота.")
    context.user_data.clear()  # Очищаем данные пользователя при старте
    try:
        update.message.reply_markdown_v2(
            fr"Привет, {user.mention_markdown_v2()}! 👋\n\nВыберите интересующий вас раздел:",
            reply_markup=main_reply_markup,
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /start: {e}")
        update.message.reply_text("Произошла ошибка. Попробуйте позже.")

def handle_main_menu(update: Update, context: CallbackContext) -> None:
    """Обрабатывает нажатия кнопок главного меню."""
    text = update.message.text
    user = update.effective_user
    logger.info(f"Пользователь {user.id} ({user.username}) нажал кнопку главного меню: {text}")
    try:
        if text == 'Погода':
            weather.show_weather_menu(update, context)  # Переходим к меню погоды
            context.user_data['current_module'] = 'weather'
        elif text == 'Курс валют':
            currency.show_currency_menu(update, context)  # TODO: Создать эту функцию
            context.user_data['current_module'] = 'currency'
        elif text == 'Воздушная тревога':
            air_raid.show_air_raid_menu(update, context)  # TODO: Создать эту функцию
            context.user_data['current_module'] = 'air_raid'
        elif text == 'Новости ТЦК':
            tcc_news.show_tcc_news_menu(update, context)  # TODO: Создать эту функцию
            context.user_data['current_module'] = 'tcc_news'
        else:
            update.message.reply_text("Не понимаю ваш запрос.")
    except Exception as e:
        logger.error(f"Ошибка при обработке главного меню ({text}) от пользователя {user.id}: {e}")
        update.message.reply_text("Произошла ошибка при обработке запроса. Попробуйте позже.")

def handle_module_buttons(update: Update, context: CallbackContext) -> None:
    """Обрабатывает нажатия кнопок внутри модулей."""
    text = update.message.text
    user = update.effective_user
    current_module = context.user_data.get('current_module')
    logger.info(f"Пользователь {user.id} ({user.username}) нажал кнопку '{text}' в модуле '{current_module}'")
    try:
        if current_module == 'weather':
            button_handlers.handle_weather_buttons(update, context)
        elif current_module == 'currency':
            button_handlers.handle_currency_buttons(update, context)
        elif current_module == 'air_raid':
            button_handlers.handle_air_raid_buttons(update, context)
        elif current_module == 'tcc_news':
            button_handlers.handle_tcc_news_buttons(update, context)
        elif text == 'Вернуться в главное меню':
            start(update, context)
            context.user_data.pop('current_module', None) # Удаляем информацию о текущем модуле
        else:
            update.message.reply_text("Не понимаю ваш запрос в этом разделе.")
    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки '{text}' в модуле '{current_module}' от пользователя {user.id}: {e}")
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

    # Обработчик нажатий кнопок главного меню
    dispatcher.add_handler(MessageHandler(filters.text & ~filters.command, handle_main_menu))

    # Обработчик нажатий кнопок внутри модулей
    dispatcher.add_handler(MessageHandler(filters.text & ~filters.command, handle_module_buttons))

    # Обработчик ошибок
    dispatcher.add_error_handler(error_handler)

    # Запускаем бота
    updater.start_polling()

    # Бот будет работать до тех пор, пока вы не нажмете Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main()