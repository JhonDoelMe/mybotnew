import os
import aiohttp
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
from database import get_connection, get_user_settings, update_user_setting
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

ALERTS_API_URL = "https://api.alerts.in.ua/v1/alerts/active.json"
ALERTS_API_TOKEN = os.getenv("ALERTS_IN_UA_TOKEN")

# Список областей
OBLASTS = {
    "3": "Хмельницька область", "4": "Вінницька область", "5": "Рівненська область",
    "8": "Волинська область", "9": "Дніпропетровська область", "10": "Житомирська область",
    "11": "Закарпатська область", "12": "Запорізька область", "13": "Івано-Франківська область",
    "14": "Київська область", "15": "Кіровоградська область", "16": "Луганська область",
    "17": "Миколаївська область", "18": "Одеська область", "19": "Полтавська область",
    "20": "Сумська область", "21": "Тернопільська область", "22": "Харківська область",
    "23": "Херсонська область", "24": "Черкаська область", "25": "Чернігівська область",
    "26": "Чернівецька область", "27": "Львівська область", "28": "Донецька область",
    "29": "Автономна Республіка Крим", "30": "м. Севастополь", "31": "м. Київ"
}

# Загружаем список локаций из JSON
with open('locations.json', 'r', encoding='utf-8') as f:
    LOCATIONS = json.load(f)

async def show_air_raid_menu(update: Update, context: CallbackContext):
    """Показать меню тревог"""
    user_id = update.effective_user.id
    with get_connection() as conn:
        settings = get_user_settings(conn, user_id)
        
        status = "включены" if settings['notify_air_alerts'] else "выключены"
        oblast = OBLASTS.get(settings['oblast_uid'], "не выбрана")
        location_uid = settings['location_uid']
        location = next((name for uid, name in LOCATIONS.get(settings['oblast_uid'], {}).items() 
                        if uid == location_uid), "не выбран") if location_uid else "не выбран"
        
        keyboard = [
            ['Проверить тревоги'],
            ['Выбрать область'],
            ['Выбрать город'],
            ['Отключить уведомления' if settings['notify_air_alerts'] else 'Включить уведомления'],
            ['Вернуться в главное меню']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"Уведомления: {status}\n"
            f"Область: {oblast}\n"
            f"Локация: {location}",
            reply_markup=reply_markup
        )
    return settings

async def select_oblast(update: Update, context: CallbackContext):
    """Показать список областей для выбора"""
    keyboard = [[oblast] for oblast in OBLASTS.values()]
    keyboard.append(['Вернуться в меню тревог'])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите область:", reply_markup=reply_markup)
    context.user_data['awaiting_oblast'] = True

async def select_location(update: Update, context: CallbackContext):
    """Показать список локаций в выбранной области"""
    user_id = update.effective_user.id
    with get_connection() as conn:
        settings = get_user_settings(conn, user_id)
        oblast_uid = settings['oblast_uid']
    
    if not oblast_uid:
        await update.message.reply_text("Сначала выберите область!")
        return
    
    locations = LOCATIONS.get(oblast_uid, {})
    if not locations:
        await update.message.reply_text("Нет доступных локаций для этой области.")
        return
    
    keyboard = [[name] for name in locations.values()]
    keyboard.append(['Вернуться в меню тревог'])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите город или громаду:", reply_markup=reply_markup)
    context.user_data['awaiting_location'] = True

async def check_air_raid(update: Update, context: CallbackContext):
    """Проверить статус тревог в выбранной локации"""
    if not ALERTS_API_TOKEN:
        await update.message.reply_text("Ошибка: API-токен для alerts.in.ua не настроен")
        return
    
    user_id = update.effective_user.id
    with get_connection() as conn:
        settings = get_user_settings(conn, user_id)
        location_uid = settings['location_uid']
    
    try:
        params = {"token": ALERTS_API_TOKEN}
        async with aiohttp.ClientSession() as session:
            async with session.get(ALERTS_API_URL, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 401:
                    await update.message.reply_text("Ошибка: Неверный или просроченный API-токен для alerts.in.ua")
                    return
                response.raise_for_status()
                data = await response.json()
        
        alerts = data.get("alerts", [])
        if not location_uid:  # Если локация не выбрана, показываем все активные тревоги
            active_alerts = [alert["location_title"] for alert in alerts if alert.get("finished_at") is None]
        else:  # Фильтруем по выбранной локации
            active_alerts = [alert["location_title"] for alert in alerts 
                            if alert.get("finished_at") is None and alert.get("location_uid") == location_uid]
        
        if active_alerts:
            message = "🚨 Тревога в:\n" + "\n".join(active_alerts)
        else:
            message = "✅ Нет активных тревог в выбранной локации"
            
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Air raid error: {e}")
        await update.message.reply_text("Ошибка проверки тревог")

async def toggle_notifications(update: Update, context: CallbackContext):
    """Переключить уведомления"""
    user_id = update.effective_user.id
    with get_connection() as conn:
        settings = get_user_settings(conn, user_id)
        new_status = not settings['notify_air_alerts']
        update_user_setting(conn, user_id, 'notify_air_alerts', int(new_status))
        
        status = "включены" if new_status else "выключены"
        await update.message.reply_text(f"Уведомления {status}")
        await show_air_raid_menu(update, context)

async def handle_air_raid_input(update: Update, context: CallbackContext):
    """Обработка выбора области и города"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if 'awaiting_oblast' in context.user_data:
        oblast_uid = next((uid for uid, name in OBLASTS.items() if name == text), None)
        if oblast_uid:
            with get_connection() as conn:
                update_user_setting(conn, user_id, 'oblast_uid', oblast_uid)
                update_user_setting(conn, user_id, 'location_uid', None)  # Сбрасываем город
                conn.commit()
            await update.message.reply_text(f"Выбрана область: {text}")
            del context.user_data['awaiting_oblast']
            settings = await show_air_raid_menu(update, context)
            logger.info(f"After oblast selection, settings: {settings}")
        elif text == 'Вернуться в меню тревог':
            del context.user_data['awaiting_oblast']
            await show_air_raid_menu(update, context)
        else:
            await update.message.reply_text("Выберите область из списка!")
    
    elif 'awaiting_location' in context.user_data:
        with get_connection() as conn:
            settings = get_user_settings(conn, user_id)
            oblast_uid = settings['oblast_uid']
        
        locations = LOCATIONS.get(oblast_uid, {})
        location_uid = next((uid for uid, name in locations.items() if name == text), None)
        
        if location_uid:
            with get_connection() as conn:
                update_user_setting(conn, user_id, 'location_uid', location_uid)
                conn.commit()
            await update.message.reply_text(f"Выбрана локация: {text}")
            del context.user_data['awaiting_location']
            settings = await show_air_raid_menu(update, context)
            logger.info(f"After location selection, settings: {settings}")
        elif text == 'Вернуться в меню тревог':
            del context.user_data['awaiting_location']
            await show_air_raid_menu(update, context)
        else:
            await update.message.reply_text("Выберите локацию из списка!")
    
    else:
        if text == 'Проверить тревоги':
            await check_air_raid(update, context)
        elif text == 'Выбрать область':
            await select_oblast(update, context)
        elif text == 'Выбрать город':
            await select_location(update, context)
        elif text in ('Включить уведомления', 'Отключить уведомления'):
            await toggle_notifications(update, context)
        elif text == 'Вернуться в главное меню':
            from button_handlers import main_reply_markup
            await update.message.reply_text("Главное меню", reply_markup=main_reply_markup)
            context.user_data.clear()