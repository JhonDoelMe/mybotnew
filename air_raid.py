import requests
import logging
import asyncio
from typing import Dict, List, Optional, Any, Set, Tuple
from asyncio import Semaphore

import telegram
from telegram.ext import ContextTypes
from telegram.error import BadRequest, Forbidden

import database as db
import config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

LAST_STATUS_KEY = 'last_alert_status'

async def get_air_raid_status(context: Optional[ContextTypes.DEFAULT_TYPE] = None) -> Optional[List[Dict[str, Any]]]:
    """
    Fetches current air raid status from UkraineAlarm API.

    Args:
        context: Telegram context to access bot_data for caching lastUpdate.

    Returns:
        Optional[List[Dict[str, Any]]]: List of active alerts or None on error.
    """
    api_url = config.cfg.get('AIR_RAID_API_URL')
    auth_token = config.cfg.get('UKRAINE_ALARM_TOKEN')

    if not api_url or not auth_token:
        logger.error("Air Raid API URL or Auth Token is not configured.")
        return None

    headers = {'Authorization': auth_token}
    if context and LAST_STATUS_KEY in context.bot_data:
        last_update = context.bot_data.get(LAST_STATUS_KEY, {}).get('lastUpdate')
        if last_update:
            headers['If-Modified-Since'] = last_update

    try:
        response = requests.get(api_url, headers=headers, timeout=15)
        if response.status_code == 304:
            logger.info("No new air raid data since last update.")
            return context.bot_data.get(LAST_STATUS_KEY, {}).get('data', [])
        response.raise_for_status()

        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list):
                    last_update = response.headers.get('Last-Modified', '')
                    if context:
                        context.bot_data[LAST_STATUS_KEY] = {'data': data, 'lastUpdate': last_update}
                    return data
                logger.error(f"Unexpected API response type: {type(data)}. Expected list.")
                return None
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON: {e}")
                return None
        else:
            logger.error(f"API request failed with status {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching air raid status: {e}")
        return None

def format_alert_message(region_name: str, alert_type: Optional[str] = None) -> str:
    """
    Formats an air raid alert message.

    Args:
        region_name: Name of the region.
        alert_type: Type of alert, if any.

    Returns:
        str: Formatted message for Telegram.
    """
    type_str = f" ({alert_type})" if alert_type else ""
    return f"🚨 УВАГА! Повітряна тривога в **{region_name}**!{type_str}\nПрямуйте до укриття!"

def format_no_alert_message(region_name: str) -> str:
    """
    Formats an air raid all-clear message.

    Args:
        region_name: Name of the region.

    Returns:
        str: Formatted message for Telegram.
    """
    return f"✅ Відбій повітряної тривоги в **{region_name}**."

async def send_notifications(
    tasks: List[telegram.Bot.send_message],
    context: ContextTypes.DEFAULT_TYPE,
    max_concurrent: int = 20
) -> Tuple[int, int]:
    """
    Sends notifications with concurrency limit.

    Args:
        tasks: List of send_message tasks.
        context: Telegram context.
        max_concurrent: Maximum concurrent messages.

    Returns:
        Tuple[int, int]: (success_count, fail_count).
    """
    semaphore = Semaphore(max_concurrent)

    async def send_with_semaphore(task):
        async with semaphore:
            try:
                await task
                return None
            except Exception as e:
                return e

    results = await asyncio.gather(*(send_with_semaphore(task) for task in tasks), return_exceptions=True)
    success_count = sum(1 for r in results if r is None)
    fail_count = len(tasks) - success_count

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            user_id = tasks[i].chat_id
            if isinstance(result, Forbidden):
                logger.info(f"Removing user {user_id} due to Forbidden error.")
                db.remove_subscriber(user_id)
            logger.error(f"Failed to send to {user_id}: {result}")

    return success_count, fail_count

async def check_air_raid_status(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Checks air raid status, compares with previous state, and sends notifications.

    Args:
        context: Telegram context containing bot_data.
    """
    logger.info("Checking air raid status...")
    current_alerts_list = await get_air_raid_status(context)
    if current_alerts_list is None:
        logger.warning("Could not fetch air raid status. Skipping check.")
        return

    last_status: Dict[str, Dict[str, Any]] = context.bot_data.get(LAST_STATUS_KEY, {}).get('data', {})
    current_status: Dict[str, Dict[str, Any]] = {}
    current_active_regions: Dict[str, Set[str]] = {}

    # Process current data
    for alert_region in current_alerts_list:
        region_id = alert_region.get('regionId')
        if not region_id:
            logger.warning(f"Alert region missing 'regionId': {alert_region}")
            continue
        current_status[region_id] = alert_region
        active_alerts = alert_region.get('activeAlerts', [])
        if active_alerts:
            current_active_regions[region_id] = {alert.get('type', 'unknown') for alert in active_alerts}

    # Determine changes
    new_alerts: Set[str] = set()
    ended_alerts: Set[str] = set()
    changed_alerts: Dict[str, Set[str]] = {}

    for region_id in current_active_regions:
        if region_id not in last_status or not last_status[region_id].get('activeAlerts'):
            new_alerts.add(region_id)
        else:
            last_types = {alert.get('type', 'unknown') for alert in last_status[region_id].get('activeAlerts', [])}
            current_types = current_active_regions[region_id]
            if last_types != current_types:
                changed_alerts[region_id] = current_types

    for region_id in last_status:
        if region_id not in current_active_regions and last_status[region_id].get('activeAlerts'):
            ended_alerts.add(region_id)

    if not (new_alerts or ended_alerts or changed_alerts):
        logger.info("No changes in air raid status.")
        return

    logger.info(f"Changes detected - New: {len(new_alerts)}, Ended: {len(ended_alerts)}, Changed: {len(changed_alerts)}")

    tasks = []
    for region_id in new_alerts:
        subscribers = db.get_subscribers(region_id=region_id)
        if not subscribers:
            continue
        region_data = current_status.get(region_id)
        region_name = region_data.get('regionName', 'Невідомий регіон')
        alert_types = current_active_regions.get(region_id, set())
        alert_type = ', '.join(alert_types) if alert_types else None
        message = format_alert_message(region_name, alert_type)
        for user_id, _ in subscribers:
            tasks.append(context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=telegram.constants.ParseMode.MARKDOWN_V2
            ))

    for region_id in ended_alerts:
        subscribers = db.get_subscribers(region_id=region_id)
        if not subscribers:
            continue
        region_data = last_status.get(region_id)
        region_name = region_data.get('regionName', 'Невідомий регіон')
        message = format_no_alert_message(region_name)
        for user_id, _ in subscribers:
            tasks.append(context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=telegram.constants.ParseMode.MARKDOWN_V2
            ))

    for region_id, new_types in changed_alerts.items():
        subscribers = db.get_subscribers(region_id=region_id)
        if not subscribers:
            continue
        region_data = current_status.get(region_id)
        region_name = region_data.get('regionName', 'Невідомий регіон')
        alert_type = ', '.join(new_types) if new_types else None
        message = f"⚠️ Зміна тривоги в **{region_name}**: {alert_type}"
        for user_id, _ in subscribers:
            tasks.append(context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=telegram.constants.ParseMode.MARKDOWN_V2
            ))

    if tasks:
        success_count, fail_count = await send_notifications(tasks, context)
        logger.info(f"Notifications sent. Success: {success_count}, Failed: {fail_count}")