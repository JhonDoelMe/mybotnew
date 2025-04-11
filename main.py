import logging
import traceback
import sqlite3
from typing import Dict, Any, Optional

from dotenv import load_dotenv

import telegram
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, helpers
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    Application
)
from telegram.constants import ParseMode
from telegram.error import TelegramError, Forbidden, BadRequest

import config
import database as db
import air_raid
import weather
import currency

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

try:
    config.load_config()
except ValueError as e:
    logger.critical(f"Configuration error: {e}")
    exit(1)

BOT_TOKEN = config.cfg.get('BOT_TOKEN')
ADMIN_IDS = [int(id_str) for id_str in config.cfg.get('ADMIN_IDS', '').split(',') if id_str.strip().isdigit()]
AIR_RAID_CHECK_INTERVAL = config.cfg.get('AIR_RAID_CHECK_INTERVAL', 90)

MAIN_MENU = [
    ["🔔 Тревога", "💵 Курс валют"],
    ["☀️ Погода"]
]
WEATHER_MENU = [
    ["🌆 Изменить город", "🔄 Обновить прогноз"],
    ["⬅️ Назад"]
]
CURRENCY_MENU = [
    ["🔄 Обновить курс", "➕ Добавить код валюты"],
    ["⬅️ Назад"]
]
AIR_RAID_MENU = [
    ["🔄 Обновить статус", "🌍 Выбрать область"],
    ["⬅️ Назад"]
]

try:
    db.init_db()
except sqlite3.Error as e:
    logger.critical(f"Failed to initialize database: {e}")
    exit(1)

def require_message(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not update.message:
            logger.warning(f"{func.__name__} called without message")
            return
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            await update.message.reply_text(f"⚠️ Помилка: {str(e)}")
            raise
    return wrapper

@require_message
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id if user else "Unknown ID"
    first_name = helpers.escape_markdown(user.first_name, version=2) if user else "Користувач"
    logger.info(f"User {user_id} started the bot.")

    context.user_data['menu'] = 'main'
    reply_markup = ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)

    welcome_message = (
        f"Привіт, {first_name}\\!\n\n"
        "Я твій помічник\\. Обери дію з меню нижче:"
    )

    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)

@require_message
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else "Unknown ID"
    logger.info(f"User {user_id} requested help.")

    help_text = (
        "Ось що я вмію:\n\n"
        "*Основне меню:*\n"
        "\\- 🔔 *Тревога*: Статус тривог та підписка\\.\n"
        "\\- 💵 *Курс валют*: Курс валют\\.\n"
        "\\- ☀️ *Погода*: Прогноз погоди\\.\n\n"
        "*Команди:*\n"
        "`/start` \\- Повернення до меню\\.\n"
        "`/help` \\- Допомога\\.\n"
        "`/subscribe` \\- Підписка на тривоги\\.\n"
        "`/unsubscribe` \\- Відписка\\.\n"
        "`/status` \\- Статус підписки\\."
    )

    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN_V2)

async def resolve_region_id(region_name: str) -> Optional[str]:
    alerts = await air_raid.get_air_raid_status()
    if not alerts:
        return None
    for region in alerts:
        if region.get('regionName', '').lower() == region_name.lower():
            return region.get('regionId')
    return None

@require_message
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        return

    region = " ".join(context.args).strip() if context.args else None
    if region:
        region_id = await resolve_region_id(region)
        if not region_id:
            await update.message.reply_text("Регіон не знайдено. Спробуйте ще раз.")
            return
        if db.is_subscribed(user_id, region_id):
            await update.message.reply_text(f"Ви вже підписані на {region}.")
        elif db.add_subscriber(user_id, region_id):
            await update.message.reply_text(f"Підписано на {region}.")
        else:
            await update.message.reply_text("Помилка підписки.")
        return

    alerts = await air_raid.get_air_raid_status()
    if not alerts:
        await update.message.reply_text("Не вдалося завантажити список регіонів.")
        return

    keyboard = [
        [InlineKeyboardButton(region.get('regionName'), callback_data=f"subscribe:{region.get('regionId')}")]
        for region in sorted(alerts, key=lambda x: x.get('regionName', ''))
    ]
    keyboard.append([InlineKeyboardButton("Всі регіони", callback_data="subscribe:all")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Оберіть регіон для підписки:", reply_markup=reply_markup)

@require_message
async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        return

    region = " ".join(context.args).strip() if context.args else None
    if region:
        region_id = await resolve_region_id(region)
        if not region_id:
            await update.message.reply_text("Регіон не знайдено.")
            return
        if not db.is_subscribed(user_id, region_id):
            await update.message.reply_text(f"Ви не підписані на {region}.")
        elif db.remove_subscriber(user_id, region_id):
            await update.message.reply_text(f"Відписано від {region}.")
        else:
            await update.message.reply_text("Помилка відписки.")
        return

    if not db.is_subscribed(user_id):
        await update.message.reply_text("Ви не підписані.")
    elif db.remove_subscriber(user_id):
        await update.message.reply_text("Відписано від усіх сповіщень.")
    else:
        await update.message.reply_text("Помилка відписки.")

@require_message
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        return

    subscriptions = db.get_subscribers()
    user_regions = [r for u, r in subscriptions if u == user_id]
    if not user_regions:
        await update.message.reply_text("Ви не підписані.")
        return

    alerts = await air_raid.get_air_raid_status()
    region_names = {r.get('regionId'): r.get('regionName') for r in alerts} if alerts else {}
    message = "Ви підписані на:\n"
    for region_id in user_regions:
        name = region_names.get(region_id, "Всі регіони" if region_id is None else "Невідомий регіон")
        message += f"- {name}\n"
    await update.message.reply_text(message)

@require_message
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Доступ заборонено.")
        return

    sub_count = len(set(u for u, _ in db.get_subscribers()))
    await update.message.reply_text(f"Кількість підписників: {sub_count}")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    text = update.message.text
    user_id = update.effective_user.id if update.effective_user else "Unknown ID"
    logger.info(f"Received text from {user_id}: '{text}'")

    try:
        if text == "🔔 Тревога":
            context.user_data['menu'] = 'air_raid'
            reply_markup = ReplyKeyboardMarkup(AIR_RAID_MENU, resize_keyboard=True)
            await update.message.reply_text("Меню тривог:", reply_markup=reply_markup)
        elif text == "💵 Курс валют":
            context.user_data['menu'] = 'currency'
            reply_markup = ReplyKeyboardMarkup(CURRENCY_MENU, resize_keyboard=True)
            await update.message.reply_text("Меню валют:", reply_markup=reply_markup)
            await currency.get_currency_command(update, context)
        elif text == "☀️ Погода":
            context.user_data['menu'] = 'weather'
            reply_markup = ReplyKeyboardMarkup(WEATHER_MENU, resize_keyboard=True)
            await update.message.reply_text("Меню погоди:", reply_markup=reply_markup)
            await weather.get_weather_command(update, context)

        elif context.user_data.get('menu') == 'weather':
            if text == "🌆 Изменить город":
                await update.message.reply_text("Введіть назву міста:")
                context.user_data['awaiting_city'] = True
            elif text == "🔄 Обновить прогноз":
                context.args = [context.user_data.get('city', 'Kyiv')]
                await weather.get_weather_command(update, context, force_update=True)
            elif text == "⬅️ Назад":
                context.user_data['menu'] = 'main'
                reply_markup = ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)
                await update.message.reply_text("Повернення до основного меню:", reply_markup=reply_markup)

        elif context.user_data.get('menu') == 'currency':
            if text == "🔄 Обновить курс":
                await currency.get_currency_command(update, context, force_update=True)
            elif text == "➕ Добавить код валюты":
                await update.message.reply_text("Введіть код валюти \\(наприклад, USD, EUR\\):", parse_mode=ParseMode.MARKDOWN_V2)
                context.user_data['awaiting_currency'] = True
            elif text == "⬅️ Назад":
                context.user_data['menu'] = 'main'
                reply_markup = ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)
                await update.message.reply_text("Повернення до основного меню:", reply_markup=reply_markup)

        elif context.user_data.get('menu') == 'air_raid':
            if text == "🔄 Обновить статус":
                await air_raid.alerts_command(update, context)
            elif text == "🌍 Выбрать область":
                alerts = await air_raid.get_air_raid_status()
                if not alerts:
                    await update.message.reply_text("Не вдалося завантажити список регіонів.")
                    return
                keyboard = [
                    [InlineKeyboardButton(region.get('regionName'), callback_data=f"region:{region.get('regionId')}")]
                    for region in sorted(alerts, key=lambda x: x.get('regionName', ''))
                ]
                keyboard.append([InlineKeyboardButton("Всі регіони", callback_data="region:all")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("Оберіть область:", reply_markup=reply_markup)
            elif text == "⬅️ Назад":
                context.user_data['menu'] = 'main'
                reply_markup = ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)
                await update.message.reply_text("Повернення до основного меню:", reply_markup=reply_markup)

        elif context.user_data.get('awaiting_city'):
            context.user_data['city'] = text
            context.user_data['awaiting_city'] = False
            context.args = [text]
            await weather.get_weather_command(update, context)
        
        elif context.user_data.get('awaiting_currency'):
            currency_code = text.upper()
            context.user_data['awaiting_currency'] = False
            if currency.add_currency_code(user_id, currency_code):
                await update.message.reply_text(f"Додано валюту {currency_code}.")
                await currency.get_currency_command(update, context)
            else:
                await update.message.reply_text("Невірний код валюти або помилка додавання.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Помилка: {str(e)}")
        raise

async def button_callback(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    action, data = query.data.split(':')

    try:
        if action == "subscribe":
            region_id = None if data == 'all' else data
            if db.is_subscribed(user_id, region_id):
                await query.message.reply_text("Ви вже підписані на цей регіон.")
                return
            if db.add_subscriber(user_id, region_id):
                alerts = await air_raid.get_air_raid_status()
                region_name = next(
                    (r.get('regionName') for r in alerts if r.get('regionId') == region_id),
                    'всі регіони'
                ) if alerts else 'всі регіони'
                await query.message.reply_text(f"Підписано на {region_name}.")
            else:
                await query.message.reply_text("Помилка підписки.")
        
        elif action == "region":
            region_id = None if data == 'all' else data
            context.user_data['selected_region'] = region_id
            alerts = await air_raid.get_air_raid_status()
            region_name = next(
                (r.get('regionName') for r in alerts if r.get('regionId') == region_id),
                'всі регіони'
            ) if alerts else 'всі регіони'
            await query.message.reply_text(f"Обрано область: {region_name}. Тривоги будуть відображатися лише для неї.")
            await air_raid.alerts_command(update, context)
    except Exception as e:
        await query.message.reply_text(f"⚠️ Помилка: {str(e)}")
        raise

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.error is None:
        logger.warning(f"Error handler called without error. Update: {update}")
        return

    logger.error("Exception occurred:", exc_info=context.error)
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    chat_id = update.effective_chat.id if isinstance(update, Update) and update.effective_chat else None
    if chat_id:
        error_message = f"⚠️ Помилка: {str(context.error)}"
        await context.bot.send_message(chat_id=chat_id, text=error_message)

async def cleanup_subscribers(context: ContextTypes.DEFAULT_TYPE) -> None:
    subscribers = db.get_subscribers()
    for user_id, _ in set((u, r) for u, r in subscribers):
        try:
            await context.bot.send_chat_action(chat_id=user_id, action='typing')
        except telegram.error.Forbidden:
            db.remove_subscriber(user_id)
            logger.info(f"Removed inactive subscriber {user_id}")

def main():
    logger.info("Starting bot...")
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("weather", weather.get_weather_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_error_handler(error_handler)

    job_queue = application.job_queue
    if job_queue:
        try:
            interval = int(AIR_RAID_CHECK_INTERVAL)
            if interval <= 0:
                interval = 90
                logger.warning("Invalid AIR_RAID_CHECK_INTERVAL. Using default: 90.")
            job_queue.run_repeating(air_raid.check_air_raid_status, interval=interval, first=10)
            job_queue.run_repeating(cleanup_subscribers, interval=604800, first=86400)
        except (ValueError, TypeError):
            logger.error("Invalid AIR_RAID_CHECK_INTERVAL. Using default: 90.")
            job_queue.run_repeating(air_raid.check_air_raid_status, interval=90, first=10)

    logger.info("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()