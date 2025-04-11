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

ALERTS_API_URL = "https://api.ukrainealarm.com/api/v3/alerts/active"
REGIONS_API_URL = "https://api.ukrainealarm.com/api/v3/regions"
ALERTS_API_TOKEN = os.getenv("UKRAINE_ALARM_API_TOKEN")

async def show_air_raid_menu(update: Update, context: CallbackContext):
    """Показать меню тревог"""
    user_id = update.effective_user.id
    with get_connection() as conn:
        settings = get_user_settings(conn, user_id)
        
        status = "включены" if settings['notify_air_alerts'] else "выключены"
        region_id = settings.get('region_id', None)
        region_name = settings.get('region_name', "не выбрана")  # Храним имя для удобства
        
        keyboard = [
            ['🔍 Проверить тревоги'],
            ['🌍 Выбрать регион'],
            ['🔔 Включить уведомления' if not settings['notify_air_alerts'] else '🔕 Отключить уведомления'],
            ['⬅️ Вернуться в главное меню']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"Уведомления: {status}\n"
            f"Регион: {region_name}",
            reply_markup=reply_markup
        )
    return settings

async def select_region(update: Update, context: CallbackContext):
    """Показать список регионов для выбора"""
    if not ALERTS_API_TOKEN:
        await update.message.reply_text("Ошибка: API-токен для ukrainealarm.com не настроен")
        return
    
    try:
        headers = {"Authorization": ALERTS_API_TOKEN}
        async with aiohttp.ClientSession() as session:
            async with session.get(REGIONS_API_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 401:
                    await update.message.reply_text("Ошибка: Неверный API-токен")
                    return
                response.raise_for_status()
                regions = await response.json()
        
        # Фильтруем только области (State)
        keyboard = [[region["regionName"]] for region in regions if region["regionType"] == "State"]
        keyboard.append(['⬅️ Вернуться в меню тревог'])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Выберите регион:", reply_markup=reply_markup)
        context.user_data['awaiting_region'] = True
    except Exception as e:
        logger.error(f"Ошибка загрузки регионов: {e}")
        await update.message.reply_text("Ошибка загрузки списка регионов")

async def check_air_raid(update: Update, context: CallbackContext):
    """Проверить статус тревог в выбранной локации"""
    if not ALERTS_API_TOKEN:
        await update.message.reply_text("Ошибка: API-токен для ukrainealarm.com не настроен")
        return
    
    user_id = update.effective_user.id
    with get_connection() as conn:
        settings = get_user_settings(conn, user_id)
        region_id = settings.get('region_id')
    
    try:
        headers = {"Authorization": ALERTS_API_TOKEN}
        async with aiohttp.ClientSession() as session:
            async with session.get(ALERTS_API_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 401:
                    await update.message.reply_text("Ошибка: Неверный API-токен")
                    return
                response.raise_for_status()
                data = await response.json()
        
        active_alerts = []
        if not region_id:
            active_alerts = [region["regionName"] for region in data if region["activeAlerts"]]
        else:
            for region in data:
                if region["regionId"] == region_id and region["activeAlerts"]:
                    active_alerts.append(region["regionName"])
        
        if active_alerts:
            message = "🚨 Тревога в:\n" + "\n".join(active_alerts)
        else:
            message = "✅ Нет активных тревог в выбранном регионе"
            
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
    """Обработка выбора региона и переключения уведомлений"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if 'awaiting_region' in context.user_data:
        try:
            headers = {"Authorization": ALERTS_API_TOKEN}
            async with aiohttp.ClientSession() as session:
                async with session.get(REGIONS_API_URL, headers=headers) as response:
                    regions = await response.json()
            
            region = next((r for r in regions if r["regionName"] == text and r["regionType"] == "State"), None)
            if region:
                with get_connection() as conn:
                    update_user_setting(conn, user_id, 'region_id', region["regionId"])
                    update_user_setting(conn, user_id, 'region_name', region["regionName"])
                    conn.commit()
                await update.message.reply_text(f"Выбран регион: {text}")
                del context.user_data['awaiting_region']
                settings = await show_air_raid_menu(update, context)
                logger.info(f"After region selection, settings: {settings}")
            elif text == '⬅️ Вернуться в меню тревог':
                del context.user_data['awaiting_region']
                await show_air_raid_menu(update, context)
            else:
                await update.message.reply_text("Выберите регион из списка!")
        except Exception as e:
            logger.error(f"Ошибка при выборе региона: {e}")
            await update.message.reply_text("Ошибка при выборе региона")
    
    else:
        if text == '🔍 Проверить тревоги':
            await check_air_raid(update, context)
        elif text == '🌍 Выбрать регион':
            await select_region(update, context)
        elif text in ('🔔 Включить уведомления', '🔕 Отключить уведомления'):
            await toggle_notifications(update, context)
        elif text == '⬅️ Вернуться в главное меню':
            from button_handlers import main_reply_markup
            await update.message.reply_text("Главное меню", reply_markup=main_reply_markup)
            context.user_data.clear()