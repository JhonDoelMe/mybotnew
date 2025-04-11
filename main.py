# main.py
import logging
import json
import os
from typing import Dict, Any, cast

from dotenv import load_dotenv

import telegram
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    PicklePersistence # Пример, если захотите сохранять bot_data
)
from telegram.constants import ParseMode
from telegram.error import TelegramError

# Локальные импорты
import config # Модуль для загрузки конфигурации
import database as db
import air_raid
import weather
import currency
from constants import BTN_CURRENCY, BTN_WEATHER, BTN_AIR_RAID # Импорт констант кнопок

# Загрузка переменных окружения из .env файла (если он есть)
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
# Устанавливаем уровень логирования для httpx (чтобы избежать спама DEBUG логами)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Загрузка конфигурации ---
try:
    config.load_config() # Загружаем данные из config.json в config.cfg
except ValueError as e:
    logger.critical(f"Configuration error: {e}")
    exit(1) # Выход, если конфигурация не загружена

BOT_TOKEN = config.cfg.get('BOT_TOKEN')
ADMIN_ID_STR = config.cfg.get('ADMIN_ID')
AIR_RAID_CHECK_INTERVAL = config.cfg.get('AIR_RAID_CHECK_INTERVAL', 90) # Интервал в секундах, по умолчанию 90

if not BOT_TOKEN:
    logger.critical("BOT_TOKEN not found in config or environment variables!")
    exit(1)

ADMIN_ID: int | None = None
if ADMIN_ID_STR:
    try:
        ADMIN_ID = int(ADMIN_ID_STR)
    except ValueError:
        logger.warning("ADMIN_ID is present but not a valid integer. Admin commands will not work.")

# --- Инициализация Базы Данных ---
try:
    db.init_db()
except sqlite3.Error as e:
    logger.critical(f"Failed to initialize database: {e}. Exiting.")
    exit(1)


# --- Команды ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение и клавиатуру."""
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot.")

    # Основная клавиатура
    reply_markup = ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_CURRENCY), KeyboardButton(BTN_WEATHER)],
            [KeyboardButton(BTN_AIR_RAID)]
            # Можно добавить кнопку подписки/отписки сюда же
            # [KeyboardButton("/subscribe"), KeyboardButton("/unsubscribe")]
        ],
        resize_keyboard=True
    )

    welcome_message = (
        f"Привіт, {user.first_name}!\n\n"
        "Я твій помічник. Обери дію на клавіатурі:\n"
        f"- `{BTN_CURRENCY}`: Показати актуальний курс валют.\n"
        f"- `{BTN_WEATHER}`: Дізнатись погоду (використовуй `/weather Місто` або натисни кнопку для погоди у Києві).\n"
        f"- `{BTN_AIR_RAID}`: Перевірити статус повітряної тривоги зараз.\n\n"
        "Також доступні команди:\n"
        "`/help` - Допомога\n"
        "`/subscribe` - Підписатись на сповіщення про повітряну тривогу\n"
        "`/unsubscribe` - Відписатись від сповіщень\n"
        "`/status` - Перевірити статус підписки"
    )
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет справочное сообщение."""
    logger.info(f"User {update.effective_user.id} requested help.")
    help_text = (
        "Ось що я вмію:\n\n"
        f"- *{BTN_CURRENCY}*: Показати актуальний курс готівкової валюти (USD/EUR) від ПриватБанку.\n"
        f"- *{BTN_WEATHER}*: Дізнатись погоду. Натисніть кнопку для погоди в Києві або введіть `/weather Назва міста`.\n"
        f"- *{BTN_AIR_RAID}*: Перевірити поточний статус повітряної тривоги для всіх областей.\n\n"
        "*Команди:*\n"
        "`/start` - Перезапустити бота та показати головне меню.\n"
        "`/help` - Показати це повідомлення.\n"
        "`/subscribe` - Підписатись на сповіщення про початок та відбій повітряної тривоги.\n"
        "`/unsubscribe` - Відписатись від сповіщень про тривогу.\n"
        "`/status` - Перевірити, чи ви підписані на сповіщення.\n"
        # Если есть админская команда
        # `/admin` - (Тільки для адміна) Спеціальні команди.
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN_V2)

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Подписывает пользователя на рассылку уведомлений о тревогах."""
    user_id = update.effective_user.id
    if db.is_subscribed(user_id):
        await update.message.reply_text("Ви вже підписані на сповіщення.")
        logger.info(f"User {user_id} tried to subscribe again.")
    else:
        if db.add_subscriber(user_id):
            await update.message.reply_text("Дякую! Ви підписались на сповіщення про повітряну тривогу.")
            logger.info(f"User {user_id} subscribed successfully.")
        else:
            await update.message.reply_text("Не вдалося підписати вас. Спробуйте пізніше.")
            logger.error(f"Failed to add user {user_id} to subscribers.")

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отписывает пользователя от рассылки."""
    user_id = update.effective_user.id
    if not db.is_subscribed(user_id):
        await update.message.reply_text("Ви не були підписані.")
        logger.info(f"User {user_id} tried to unsubscribe but was not subscribed.")
    else:
        if db.remove_subscriber(user_id):
            await update.message.reply_text("Ви успішно відписались від сповіщень.")
            logger.info(f"User {user_id} unsubscribed successfully.")
        else:
            await update.message.reply_text("Не вдалося відписати вас. Спробуйте пізніше.")
            logger.error(f"Failed to remove user {user_id} from subscribers.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Проверяет статус подписки пользователя."""
    user_id = update.effective_user.id
    if db.is_subscribed(user_id):
        await update.message.reply_text("Ви підписані на сповіщення про повітряну тривогу.")
    else:
        await update.message.reply_text("Ви не підписані на сповіщення.")
    logger.info(f"User {user_id} checked subscription status.")


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Пример команды только для администратора."""
    user = update.effective_user
    if ADMIN_ID and user.id == ADMIN_ID:
        logger.info(f"Admin command accessed by user {user.id}")
        sub_count = len(db.get_subscribers())
        # Пример ответа админу
        await update.message.reply_text(f"Привіт, Адмін!\nКількість підписників: {sub_count}")
        # Тут можно добавить больше админских функций
    else:
        logger.warning(f"Unauthorized access attempt to /admin by user {user.id}")
        await update.message.reply_text("Ця команда доступна тільки адміністратору.")


# --- Обработчики сообщений ---
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает текстовые сообщения, соответствующие кнопкам."""
    text = update.message.text
    user_id = update.effective_user.id
    logger.info(f"Received text message from {user_id}: '{text}'")

    if text == BTN_CURRENCY:
        await currency.get_currency_command(update, context)
    elif text == BTN_WEATHER:
        # Вызываем обработчик погоды без аргументов (будет использован город по умолчанию)
        context.args = [] # Убедимся, что args пуст для вызова по кнопке
        await weather.get_weather_command(update, context)
    elif text == BTN_AIR_RAID:
        # Получаем текущий статус и отправляем пользователю
        # Не используем фоновую задачу, а делаем запрос по требованию
        logger.info(f"User {user_id} requested current air raid status via button.")
        current_alerts_list = await air_raid.get_air_raid_status()
        if current_alerts_list is None:
             await update.message.reply_text("Не вдалося отримати статус тривог зараз. Спробуйте пізніше.")
             return

        active_regions = []
        for alert_region in current_alerts_list:
             if alert_region.get('activeAlerts'):
                 region_name = alert_region.get('regionName', 'Невідомий регіон')
                 # Можно добавить тип тревоги, если нужно
                 # alert_type = alert_region['activeAlerts'][0].get('type')
                 active_regions.append(region_name)

        if not active_regions:
            response_message = "✅ На даний момент повітряної тривоги немає."
        else:
            response_message = "🚨 УВАГА! Зараз повітряна тривога в:\n\n"
            response_message += "\n".join([f"- **{name}**" for name in active_regions])
            response_message += "\n\nПрямуйте до укриття!"

        await update.message.reply_text(response_message, parse_mode=ParseMode.MARKDOWN_V2)

    else:
        # Если текст не соответствует кнопкам, можно добавить стандартный ответ
        # await update.message.reply_text("Не розумію вас. Скористайтесь кнопками або командами.")
        logger.debug(f"Unhandled text message from {user_id}: '{text}'")


# --- Обработчик ошибок ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логирует ошибки, вызванные Updates."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    # Попытка извлечь детали для лога
    update_details = "N/A"
    chat_id = "N/A"
    user_id = "N/A"

    if isinstance(update, Update):
        update_details = update.to_dict() # Логируем весь update (может быть многословно)
        if update.effective_chat:
            chat_id = update.effective_chat.id
        if update.effective_user:
            user_id = update.effective_user.id

    # Собираем traceback
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Формируем сообщение об ошибке
    error_message = (
        f"An exception was raised while handling an update\n"
        f"Update: {json.dumps(update_details, indent=2, ensure_ascii=False)}\n" # Логируем сам update
        f"Chat ID: {chat_id}\n"
        f"User ID: {user_id}\n"
        f"Context: {context}\n" # Логируем контекст (может содержать bot_data, user_data)
        f"Error: {context.error}\n"
        f"Traceback:\n{tb_string}"
    )

    # Логируем ошибку
    logger.error(error_message)

    # Можно отправить сообщение пользователю или админу об ошибке
    if ADMIN_ID:
        # Ограничиваем длину сообщения для Telegram
        admin_message = f"Bot Error: {context.error}\nUpdate: {update}\nSee logs for details."
        if len(admin_message) > 4096:
            admin_message = admin_message[:4090] + "..."
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message)
        except Exception as e:
            logger.error(f"Failed to send error notification to admin: {e}")

# --- Основная функция ---
def main() -> None:
    """Запускает бота."""
    logger.info("Starting bot...")

    # --- Persistence (Опционально) ---
    # Если вы хотите, чтобы bot_data (где хранится last_status) сохранялся между перезапусками
    # persistence = PicklePersistence(filepath="bot_persistence.pkl")
    # application = ApplicationBuilder().token(BOT_TOKEN).persistence(persistence).build()
    # --------------------------------

    # --- Application Builder ---
    # Создаем Application без персистентности (bot_data будет в памяти)
    application = ApplicationBuilder().token(BOT_TOKEN).build()


    # --- Регистрация обработчиков ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("admin", admin_command))

    # Команды с аргументами
    application.add_handler(CommandHandler("weather", weather.get_weather_command)) # /weather City Name

    # Обработчик текстовых сообщений (для кнопок и прочего)
    # Filters.TEXT & (~filters.COMMAND) - обрабатывает текстовые сообщения, не являющиеся командами
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # Обработчик ошибок
    application.add_error_handler(error_handler)

    # --- Запуск фоновой задачи ---
    job_queue = application.job_queue
    if job_queue:
         # Запускаем проверку тревог каждые AIR_RAID_CHECK_INTERVAL секунд
         # first=10 - первая проверка через 10 секунд после старта
         job_queue.run_repeating(air_raid.check_air_raid_status, interval=AIR_RAID_CHECK_INTERVAL, first=10)
         logger.info(f"Scheduled air raid check every {AIR_RAID_CHECK_INTERVAL} seconds.")
    else:
         logger.warning("JobQueue is not available. Air raid checks will not run.")


    # --- Запуск бота ---
    logger.info("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    import traceback # Импорт здесь, чтобы не загромождать верхнюю часть
    import sqlite3 # Импорт здесь для обработки ошибки init_db
    main()