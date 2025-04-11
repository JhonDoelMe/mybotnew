import asyncio
import logging
from typing import Dict, Set, Optional, List
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from telegram.error import Forbidden, BadRequest, TelegramError
from telegram.ext import ContextTypes

import config
import database as db

logger = logging.getLogger(__name__)

# Словарь перевода типов тревог
ALERT_TYPES_TRANSLATION = {
    'AIR': 'Повітряна тривога',
    'ARTILLERY': 'Артилерія',
    'URBAN_FIGHTS': 'Міські бої',
    'MISSILE': 'Ракетна загроза',  # Возможный тип, добавлен предположительно
    'CHEMICAL': 'Хімічна загроза'  # Возможный тип, добавлен предположительно
}

async def get_air_raid_status(context: Optional[ContextTypes.DEFAULT_TYPE] = None) -> Optional[List[Dict]]:
    api_url = config.cfg.get('AIR_RAID_API_URL')
    auth_token = config.cfg.get('UKRAINE_ALARM_TOKEN')
    if not api_url or not auth_token:
        logger.error("Air Raid API URL or Auth Token is not configured.")
        return None

    logger.debug(f"Using auth token: '{auth_token}'")  # Добавлено для отладки
    headers = {
        'Authorization': auth_token,
        'accept': 'application/json'
    }
    if context and 'last_alert_status' in context.bot_data:
        last_update = context.bot_data['last_alert_status'].get('lastUpdate')
        if last_update:
            headers['If-Modified-Since'] = last_update

    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        # ... остальной код без изменений
        if response.status_code == 304 and context:
            logger.info("Air raid status not modified since last check.")
            return context.bot_data['last_alert_status']['data']
        if response.status_code == 200:
            data = response.json()
            logger.debug(f"Air raid status fetched: {len(data)} regions.")
            return data
        logger.error(f"Air raid API returned status {response.status_code}: {response.text}")
        return None
    except requests.RequestException as e:
        logger.error(f"Failed to fetch air raid status: {e}")
        return None

def format_alert_message(region_name: str, alert_types: str = None) -> str:
    """
    Formats an alert message for an active air raid.

    Args:
        region_name: Name of the region.
        alert_types: Comma-separated string of translated alert types (optional).

    Returns:
        Formatted message string.
    """
    alert_type_str = f" ({alert_types})" if alert_types else ""
    return f"🚨 УВАГА! Тривога в **{region_name}**!{alert_type_str}\nПрямуйте до укриття!"

def format_no_alert_message(region_name: str) -> str:
    """
    Formats a message for when an air raid alert is cleared.

    Args:
        region_name: Name of the region.

    Returns:
        Formatted message string.
    """
    return f"✅ Відбій тривоги в **{region_name}**."

async def notify_user(context: ContextTypes.DEFAULT_TYPE, user_id: int, message: str) -> None:
    """
    Sends a notification to a user.

    Args:
        context: Bot context.
        user_id: Telegram user ID.
        message: Message to send.
    """
    try:
        delay = float(config.cfg.get('NOTIFICATION_DELAY', 0.1))
        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode='Markdown',
            disable_notification=False
        )
        await asyncio.sleep(delay)  # Avoid hitting rate limits
    except Forbidden:
        logger.info(f"User {user_id} blocked the bot or chat not found.")
        db.remove_subscriber(user_id)
    except BadRequest as e:
        logger.warning(f"Bad request for user {user_id}: {e}")
    except TelegramError as e:
        logger.error(f"Failed to notify user {user_id}: {e}")

async def check_air_raid_status(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Periodically checks air raid status and notifies subscribers of changes.

    Args:
        context: Bot context for accessing bot_data and sending messages.
    """
    logger.info("Checking air raid status...")
    current_status = await get_air_raid_status(context)
    if current_status is None:
        logger.error("Failed to fetch air raid status.")
        return

    # Храним предыдущее состояние в bot_data
    bot_data = context.bot_data.setdefault('last_alert_status', {'data': [], 'lastUpdate': None})
    last_status = {region['regionId']: region for region in bot_data['data']}
    current_active_regions: Set[str] = {region['regionId'] for region in current_status if region.get('activeAlerts')}

    # Получаем подписчиков
    subscribers = db.get_subscribers()
    subscribers_dict: Dict[int, Set[Optional[str]]] = {}
    for user_id, region_id in subscribers:
        if not isinstance(region_id, (str, type(None))):
            logger.error(f"Invalid region_id type from database: {region_id} (type: {type(region_id)})")
            continue
        subscribers_dict.setdefault(user_id, set()).add(region_id)

    for user_id, regions in subscribers_dict.items():
        try:
            regions = regions if None not in regions else {None}
            for region_id in regions:
                if region_id is None:  # Подписка на все регионы
                    for region in current_status:
                        region_id_str = region['regionId']
                        was_active = bool(last_status.get(region_id_str, {}).get('activeAlerts'))
                        is_active = region_id_str in current_active_regions
                        if is_active and not was_active:
                            alert_types = [ALERT_TYPES_TRANSLATION.get(a.get('type', 'Невідомо'), a.get('type', 'Невідомо')) 
                                         for a in region.get('activeAlerts', [])]
                            message = format_alert_message(region['regionName'], ", ".join(alert_types))
                            await notify_user(context, user_id, message)
                        elif was_active and not is_active:
                            message = format_no_alert_message(region['regionName'])
                            await notify_user(context, user_id, message)
                else:  # Конкретный регион
                    was_active = bool(last_status.get(region_id, {}).get('activeAlerts'))
                    is_active = region_id in current_active_regions
                    if is_active and not was_active:
                        region_data = next((r for r in current_status if r['regionId'] == region_id), None)
                        if region_data:
                            alert_types = [ALERT_TYPES_TRANSLATION.get(a.get('type', 'Невідомо'), a.get('type', 'Невідомо')) 
                                         for a in region_data.get('activeAlerts', [])]
                            message = format_alert_message(region_data['regionName'], ", ".join(alert_types))
                            await notify_user(context, user_id, message)
                    elif was_active and not is_active:
                        message = format_no_alert_message(last_status[region_id]['regionName'])
                        await notify_user(context, user_id, message)
        except (Forbidden, BadRequest) as e:
            logger.info(f"Removing subscriber {user_id} due to {e}")
            db.remove_subscriber(user_id)
        except Exception as e:
            logger.error(f"Error notifying {user_id}: {e}", exc_info=True)

    # Обновляем состояние
    bot_data['data'] = current_status
    bot_data['lastUpdate'] = datetime.now(ZoneInfo("UTC")).isoformat()