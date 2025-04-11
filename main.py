# main.py
import logging
import json
import os
import traceback # Импорт для error_handler
import sqlite3 # Импорт для обработки ошибки init_db
from typing import Dict, Any, cast

from dotenv import load_dotenv

import telegram
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, helpers
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
from telegram.error import TelegramError, Forbidden, BadRequest # Добавлены ошибки для error_handler

# Локальные импорты
import config # Импортируем модуль config.py
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
        logging.FileHandler("bot.log", encoding='utf-8'), # Добавлена кодировка utf-8
        logging.StreamHandler()
    ]
)
# Устанавливаем уровень логирования для httpx (чтобы избежать спама DEBUG логами)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Загрузка конфигурации ---
try:
    # Загружаем данные из config.json и env в config.cfg внутри модуля config
    config.load_config()
except ValueError as e:
    logger.critical(f"Configuration error: {e}")
    exit(1) # Выход, если конфигурация не загружена
except Exception as e:
    logger.critical(f"Unexpected error loading configuration: {e}")
    exit(1)


# --- Получение значений из загруженной конфигурации ---
# Используем config.cfg для доступа к словарю конфигурации
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
    # Проверка на None перед доступом к атрибутам
    user_id = user.id if user else "Unknown ID"
    user_name = user.username if user else "Unknown Username"
    first_name = helpers.escape_markdown(user.first_name, version=2) if user else "Користувач" # Экранируем имя пользователя
    logger.info(f"User {user_id} ({user_name}) started the bot.")

    # Основная клавиатура
    reply_markup = ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_CURRENCY), KeyboardButton(BTN_WEATHER)],
            [KeyboardButton(BTN_AIR_RAID)]
        ],
        resize_keyboard=True
    )

    # Экранируем все необходимые символы для MarkdownV2
    welcome_message = (
        f"Привіт, {first_name}\\!\n\n"
        "Я твій помічник\\.\n\nОбери дію на клавіатурі:\n"
        f"\\- `{BTN_CURRENCY}`: Показати актуальний курс валют\\.\n" # Дефис экранирован
        f"\\- `{BTN_WEATHER}`: Дізнатись погоду \\(використовуй `/weather Місто` або натисни кнопку для погоди у Києві\\)\\.\n" # Дефис и скобки экранированы
        f"\\- `{BTN_AIR_RAID}`: Перевірити статус повітряної тривоги зараз\\.\n\n" # Дефис экранирован
        "Також доступні команди:\n"
        "`/help` \\- Допомога\n"  # Дефис экранирован
        "`/subscribe` \\- Підписатись на сповіщення про повітряну тривогу\n" # Дефис экранирован
        "`/unsubscribe` \\- Відписатись від сповіщень\n" # Дефис экранирован
        "`/status` \\- Перевірити статус підписки" # Дефис экранирован
    )

    if update.message:
        try:
            await update.message.reply_text(
                welcome_message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except TelegramError as e:
            logger.error(f"Error sending start message with MarkdownV2: {e}")
            # Попытка отправить без форматирования в случае ошибки
            try:
                # Удаляем MarkdownV2 экранирование для простого текста
                plain_text_message = welcome_message.replace('\\!', '!') \
                                                    .replace('\\.', '.') \
                                                    .replace('\\(', '(') \
                                                    .replace('\\)', ')') \
                                                    .replace('\\-', '-')
                await update.message.reply_text(
                    plain_text_message,
                    reply_markup=reply_markup
                )
                logger.info("Sent start message without markdown due to previous error.")
            except TelegramError as final_e:
                logger.error(f"Failed to send start message even without markdown: {final_e}")
    else:
        logger.warning("Update object in 'start' command has no message attribute.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет справочное сообщение."""
    user_id = update.effective_user.id if update.effective_user else "Unknown ID"
    logger.info(f"User {user_id} requested help.")
    # Экранируем символы для MarkdownV2
    help_text = (
        "Ось що я вмію:\n\n"
        f"\\- *{helpers.escape_markdown(BTN_CURRENCY, version=2)}*: Показати актуальний курс готівкової валюти \\(USD/EUR\\) від ПриватБанку\\.\n"
        f"\\- *{helpers.escape_markdown(BTN_WEATHER, version=2)}*: Дізнатись погоду\\. Натисніть кнопку для погоди в Києві або введіть `/weather Назва міста`\\.\n"
        f"\\- *{helpers.escape_markdown(BTN_AIR_RAID, version=2)}*: Перевірити поточний статус повітряної тривоги для всіх областей\\.\n\n"
        "*Команди:*\n"
        "`/start` \\- Перезапустити бота та показати головне меню\\.\n"
        "`/help` \\- Показати це повідомлення\\.\n"
        "`/subscribe` \\- Підписатись на сповіщення про початок та відбій повітряної тривоги\\.\n"
        "`/unsubscribe` \\- Відписатись від сповіщень про тривогу\\.\n"
        "`/status` \\- Перевірити, чи ви підписані на сповіщення\\.\n"
    )
    if update.message:
        try:
            await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN_V2)
        except TelegramError as e:
             logger.error(f"Error sending help message with MarkdownV2: {e}")
             # Попытка отправить без форматирования
             plain_help_text = help_text.replace('\\*', '*')\
                                        .replace('\\.', '.')\
                                        .replace('\\(', '(')\
                                        .replace('\\)', ')')\
                                        .replace('\\-', '-')
             try:
                 await update.message.reply_text(plain_help_text)
             except TelegramError as final_e:
                 logger.error(f"Failed to send help message even without markdown: {final_e}")

    else:
         logger.warning("Update object in 'help_command' has no message attribute.")


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Подписывает пользователя на рассылку уведомлений о тревогах."""
    if not update.effective_user:
        logger.warning("Cannot subscribe: effective_user is None.")
        return
    if not update.message:
         logger.warning("subscribe called without update.message")
         return
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
    if not update.effective_user:
        logger.warning("Cannot unsubscribe: effective_user is None.")
        return
    if not update.message:
         logger.warning("unsubscribe called without update.message")
         return
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
    if not update.effective_user:
        logger.warning("Cannot check status: effective_user is None.")
        return
    if not update.message:
         logger.warning("status called without update.message")
         return
    user_id = update.effective_user.id
    if db.is_subscribed(user_id):
        await update.message.reply_text("Ви підписані на сповіщення про повітряну тривогу.")
    else:
        await update.message.reply_text("Ви не підписані на сповіщення.")
    logger.info(f"User {user_id} checked subscription status.")


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Пример команды только для администратора."""
    user = update.effective_user
    if not user:
        logger.warning("Admin command triggered without user info.")
        return
    if not update.message:
         logger.warning("admin_command called without update.message")
         return

    if ADMIN_ID and user.id == ADMIN_ID:
        logger.info(f"Admin command accessed by user {user.id}")
        try:
            sub_count = len(db.get_subscribers())
            await update.message.reply_text(f"Привіт, Адмін!\nКількість підписників: {sub_count}")
        except Exception as e:
             logger.error(f"Error getting subscriber count in admin command: {e}")
             await update.message.reply_text("Помилка при отриманні кількості підписників.")
    else:
        logger.warning(f"Unauthorized access attempt to /admin by user {user.id}")
        await update.message.reply_text("Ця команда доступна тільки адміністратору.")


# --- Обработчики сообщений ---
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает текстовые сообщения, соответствующие кнопкам."""
    if not update.message or not update.message.text:
        logger.warning("Received update without message text in handle_text_message.")
        return

    text = update.message.text
    user_id = update.effective_user.id if update.effective_user else "Unknown ID"
    logger.info(f"Received text message from {user_id}: '{text}'")

    if text == BTN_CURRENCY:
        await currency.get_currency_command(update, context)
    elif text == BTN_WEATHER:
        context.args = [] # Убедимся, что args пуст для вызова по кнопке
        await weather.get_weather_command(update, context)
    elif text == BTN_AIR_RAID:
        logger.info(f"User {user_id} requested current air raid status via button.")
        current_alerts_list = await air_raid.get_air_raid_status()
        if current_alerts_list is None:
             await update.message.reply_text("Не вдалося отримати статус тривог зараз\\. Спробуйте пізніше\\.") # Экранируем точку
             return

        active_regions = []
        for alert_region in current_alerts_list:
             if alert_region.get('activeAlerts') and isinstance(alert_region['activeAlerts'], list) and len(alert_region['activeAlerts']) > 0:
                 region_name = alert_region.get('regionName', 'Невідомий регіон')
                 active_regions.append(region_name)

        if not active_regions:
            # Точка в конце не требует экранирования, т.к. нет форматирования
            response_message = "✅ На даний момент повітряної тривоги немає."
            parse_mode = None # Обычный текст
        else:
            response_message = "🚨 *УВАГА\\!* Зараз повітряна тривога в:\n\n" # Экранируем !
            escaped_regions = [helpers.escape_markdown(name, version=2) for name in active_regions]
            response_message += "\n".join([f"\\- {name}" for name in escaped_regions]) # Экранируем дефис
            response_message += "\n\n_Прямуйте до укриття\\!_" # Экранируем !
            parse_mode = ParseMode.MARKDOWN_V2

        await update.message.reply_text(response_message, parse_mode=parse_mode)

    else:
        logger.debug(f"Unhandled text message from {user_id}: '{text}'")


# --- Обработчик ошибок ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логирует ошибки и сообщает админу."""
    # Проверяем, содержит ли контекст ошибку
    if context.error is None:
        logger.warning(f"Error handler called without an error in context. Update: {update}")
        return

    logger.error("Exception while handling an update:", exc_info=context.error)

    # Собираем traceback
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Пытаемся извлечь детали из update
    update_str = str(update)
    update_details = "N/A"
    chat_id = "N/A"
    user_id = "N/A"

    if isinstance(update, Update):
        try:
             # Используем to_json для лучшего форматирования, если возможно
             update_details = update.to_json()
        except Exception:
             update_details = str(update) # Fallback на строку

        if update.effective_chat:
            chat_id = update.effective_chat.id
        if update.effective_user:
            user_id = update.effective_user.id

    # Формируем сообщение об ошибке для лога
    log_message = (
        f"An exception was raised while handling an update\n"
        f"---\n"
        f"Error: {context.error}\n"
        f"User ID: {user_id}\n"
        f"Chat ID: {chat_id}\n"
        f"---\n"
        f"Traceback:\n{tb_string}"
        f"---\n"
        f"Update Details:\n{update_details}\n"
        f"---"
    )
    logger.error(log_message)

    # Отправляем уведомление администратору, если он задан
    if ADMIN_ID:
        # Экранируем текст ошибки и update для Markdown V2
        escaped_error = helpers.escape_markdown(str(context.error), version=2)
        escaped_update = helpers.escape_markdown(update_str[:500], version=2) # Ограничиваем длину

        admin_message = f"⚠️ *Bot Error* ⚠️\n\n"
        admin_message += f"*Error*: `{escaped_error}`\n"
        admin_message += f"*User*: `{user_id}`, *Chat*: `{chat_id}`\n\n"
        admin_message += f"*Traceback \\(last part\\):*\n```\n{''.join(tb_list[-3:])}\n```\n\n"
        admin_message += f"*Update \\(part\\)*:\n`{escaped_update}\\.\\.\\.`"

        # Ограничиваем общую длину сообщения для Telegram
        if len(admin_message) > 4096:
            admin_message = admin_message[:4090] + "\\.\\.\\."

        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message, parse_mode=ParseMode.MARKDOWN_V2)
        except (Forbidden, BadRequest) as e:
             # Если ошибка отправки админу - BadRequest(Chat not found) или Forbidden(Blocked)
             logger.error(f"Failed to send error notification to admin {ADMIN_ID}: {e} "
                          f"(Bot might be blocked by admin or chat not found/invalid)")
        except TelegramError as e:
             logger.error(f"Telegram error sending notification to admin {ADMIN_ID}: {e}")
        except Exception as e:
            # Ловим другие возможные ошибки при отправке админу
            logger.error(f"Unexpected error sending notification to admin {ADMIN_ID}: {e}")


# --- Основная функция ---
def main() -> None:
    """Запускает бота."""
    logger.info("Starting bot...")

    # --- Persistence (Опционально) ---
    # persistence = PicklePersistence(filepath="bot_persistence.pkl")
    # application = ApplicationBuilder().token(BOT_TOKEN).persistence(persistence).build()

    # --- Application Builder ---
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # --- Регистрация обработчиков ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("weather", weather.get_weather_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_error_handler(error_handler)

    # --- Запуск фоновой задачи ---
    job_queue = application.job_queue
    if job_queue:
         try:
             check_interval_sec = int(AIR_RAID_CHECK_INTERVAL)
             if check_interval_sec <= 0:
                 check_interval_sec = 90 # Защита от невалидного значения
                 logger.warning("AIR_RAID_CHECK_INTERVAL must be positive. Using default 90 seconds.")

             job_queue.run_repeating(air_raid.check_air_raid_status, interval=check_interval_sec, first=10)
             logger.info(f"Scheduled air raid check every {check_interval_sec} seconds.")
         except (ValueError, TypeError):
             logger.error(f"Invalid AIR_RAID_CHECK_INTERVAL: '{AIR_RAID_CHECK_INTERVAL}'. Must be an integer. Using default 90 seconds.")
             job_queue.run_repeating(air_raid.check_air_raid_status, interval=90, first=10)
    else:
         logger.warning("JobQueue is not available. Air raid checks will not run.")


    # --- Запуск бота ---
    logger.info("Bot is running...")
    try:
        # allowed_updates можно убрать для простоты или настроить точнее, если нужно
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except TelegramError as e:
        logger.critical(f"Failed to start polling: {e}")
    except Exception as e:
        logger.critical(f"An unexpected error occurred during polling: {e}", exc_info=True)

if __name__ == '__main__':
    main()