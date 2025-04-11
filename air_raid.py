import os
import aiohttp
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from cachetools import TTLCache
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
from database import get_connection, get_user_settings, update_user_setting
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Конфигурация API
ALERTS_API_URL = "https://api.ukrainealarm.com/api/v3/alerts"
REGIONS_API_URL = "https://api.ukrainealarm.com/api/v3/regions"
ALERTS_API_TOKEN = os.getenv("UKRAINE_ALARM_API_TOKEN")

# Кэширование на 5 минут
REGION_CACHE = TTLCache(maxsize=100, ttl=300)
ALERT_CACHE = TTLCache(maxsize=100, ttl=60)

# Константы
MAX_RETRIES = 3
RETRY_DELAY = 2
REQUEST_TIMEOUT = 15

class UkraineAlarmAPI:
    @staticmethod
    async def _make_request(url: str, headers: Dict = None, params: Dict = None):
        """Универсальный метод для API запросов с повторными попытками"""
        headers = headers or {}
        params = params or {}
        
        if ALERTS_API_TOKEN:
            headers["Authorization"] = ALERTS_API_TOKEN
        
        async with aiohttp.ClientSession() as session:
            for attempt in range(MAX_RETRIES):
                try:
                    async with session.get(
                        url,
                        headers=headers,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                    ) as response:
                        if response.status == 429:
                            wait_time = int(response.headers.get('Retry-After', RETRY_DELAY))
                            await asyncio.sleep(wait_time)
                            continue
                            
                        response.raise_for_status()
                        return await response.json()
                        
                except aiohttp.ClientError as e:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    if attempt == MAX_RETRIES - 1:
                        raise
                    await asyncio.sleep(RETRY_DELAY)
        
        return None

    @classmethod
    async def get_regions(cls) -> List[Dict]:
        """Получить список регионов"""
        if 'regions' in REGION_CACHE:
            return REGION_CACHE['regions']
            
        regions = await cls._make_request(REGIONS_API_URL)
        if regions:
            REGION_CACHE['regions'] = regions
        return regions or []

    @classmethod
    async def get_active_alerts(cls, region_id: str = None) -> List[Dict]:
        """Получить активные тревоги"""
        cache_key = f"alerts_{region_id}" if region_id else "all_alerts"
        if cache_key in ALERT_CACHE:
            return ALERT_CACHE[cache_key]
            
        url = f"{ALERTS_API_URL}/{region_id}" if region_id else ALERTS_API_URL
        alerts = await cls._make_request(url)
        
        if alerts:
            ALERT_CACHE[cache_key] = alerts
        return alerts or []

async def show_air_raid_menu(update: Update, context: CallbackContext):
    """Показать меню тревог с текущими настройками"""
    user_id = update.effective_user.id
    with get_connection() as conn:
        settings = get_user_settings(conn, user_id)
        
        status = "🔔 Включены" if settings['notify_air_alerts'] else "🔕 Выключены"
        region_status = settings['region_name'] or "не выбран"
        
        keyboard = [
            ['🔍 Проверить тревоги'],
            ['🌍 Выбрать регион'],
            ['🔔 Вкл уведомления' if not settings['notify_air_alerts'] else '🔕 Выкл уведомления'],
            ['⬅️ Главное меню']
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"🚨 Меню воздушных тревог\n\n"
            f"Статус уведомлений: {status}\n"
            f"Регион: {region_status}",
            reply_markup=reply_markup
        )

async def select_region(update: Update, context: CallbackContext):
    """Показать список регионов для выбора"""
    if not ALERTS_API_TOKEN:
        await update.message.reply_text("⚠️ API-токен не настроен. Обратитесь к администратору.")
        return
    
    try:
        regions = await UkraineAlarmAPI.get_regions()
        if not regions:
            await update.message.reply_text("❌ Не удалось загрузить список регионов")
            return
            
        # Фильтруем только области (State) и районы (District)
        oblasts = [r for r in regions if r.get("regionType") == "State"]
        districts = [r for r in regions if r.get("regionType") == "District"]
        
        # Создаем клавиатуру с группами по 2 кнопки
        keyboard = []
        for i in range(0, len(oblasts), 2):
            row = oblasts[i:i+2]
            keyboard.append([r["regionName"] for r in row])
        
        keyboard.append(['⬅️ Назад'])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "📍 Выберите область или район:",
            reply_markup=reply_markup
        )
        context.user_data['awaiting_region'] = True
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке регионов: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка при загрузке регионов")

async def check_air_raid(update: Update, context: CallbackContext):
    """Проверить статус тревог в выбранном регионе"""
    user_id = update.effective_user.id
    with get_connection() as conn:
        settings = get_user_settings(conn, user_id)
        region_id = settings.get('region_id')
        region_name = settings.get('region_name', 'Украина')
    
    try:
        alerts = await UkraineAlarmAPI.get_active_alerts(region_id)
        if not alerts:
            await update.message.reply_text(f"✅ В {region_name} нет активных тревог")
            return
            
        active_alerts = []
        for alert in alerts:
            if alert.get("activeAlerts"):
                for alarm in alert["activeAlerts"]:
                    start_time = datetime.strptime(alarm["alertStarted"], "%Y-%m-%dT%H:%M:%S%z")
                    active_alerts.append({
                        "region": alert["regionName"],
                        "type": alarm["alertType"],
                        "start": start_time.strftime("%H:%M %d.%m.%Y"),
                        "duration": str(timedelta(seconds=alarm["duration"]))
                    })
        
        if not active_alerts:
            await update.message.reply_text(f"✅ В {region_name} нет активных тревог")
            return
            
        message = ["🚨 Активные тревоги:"]
        for alert in active_alerts:
            message.append(
                f"\n📍 {alert['region']}\n"
                f"🔹 Тип: {alert['type']}\n"
                f"⏱️ Начало: {alert['start']}\n"
                f"🕒 Длительность: {alert['duration']}"
            )
            
        await update.message.reply_text("\n".join(message))
        
    except Exception as e:
        logger.error(f"Ошибка при проверке тревог: {e}")
        await update.message.reply_text("⚠️ Не удалось проверить статус тревог")

async def toggle_notifications(update: Update, context: CallbackContext):
    """Переключить уведомления о тревогах"""
    user_id = update.effective_user.id
    with get_connection() as conn:
        settings = get_user_settings(conn, user_id)
        new_status = not settings['notify_air_alerts']
        update_user_setting(conn, user_id, 'notify_air_alerts', int(new_status))
        
        status = "включены" if new_status else "выключены"
        await update.message.reply_text(f"Уведомления {status}")
        await show_air_raid_menu(update, context)

async def handle_region_selection(update: Update, context: CallbackContext):
    """Обработать выбор региона пользователем"""
    user_id = update.effective_user.id
    selected_region = update.message.text
    
    if selected_region == '⬅️ Назад':
        context.user_data.pop('awaiting_region', None)
        await show_air_raid_menu(update, context)
        return
    
    try:
        regions = await UkraineAlarmAPI.get_regions()
        if not regions:
            await update.message.reply_text("❌ Не удалось загрузить регионы")
            return
            
        region = next((r for r in regions if r["regionName"] == selected_region), None)
        if not region:
            await update.message.reply_text("❌ Выберите регион из списка")
            return
            
        with get_connection() as conn:
            update_user_setting(conn, user_id, 'region_id', region["regionId"])
            update_user_setting(conn, user_id, 'region_name', region["regionName"])
            
        await update.message.reply_text(f"✅ Выбран регион: {region['regionName']}")
        context.user_data.pop('awaiting_region', None)
        await show_air_raid_menu(update, context)
        
    except Exception as e:
        logger.error(f"Ошибка при выборе региона: {e}")
        await update.message.reply_text("⚠️ Ошибка при выборе региона")