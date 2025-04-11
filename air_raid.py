import asyncio
import logging
from typing import Dict, Set, Optional, List
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram import helpers

import config
import database as db

logger = logging.getLogger(__name__)

ALERT_TYPES_TRANSLATION = {
    'AIR': 'Повітряна тривога',
    'ARTILLERY': 'Артилерія',
    'URBAN_FIGHTS': 'Міські бої',
    'MISSILE': 'Ракетна загроза',
    'CHEMICAL': 'Хімічна загроза'
}

async def get_air_raid_status(context: Optional[ContextTypes.DEFAULT_TYPE] = None) -> Optional[List[Dict]]:
    api_url = config.cfg.get('AIR_RAID_API_URL')
    auth_token = config.cfg.get('UKRAINE_ALARM_TOKEN')
    if not api_url or not auth_token:
        logger.error("Air Raid API URL or Auth Token is not configured.")
        return None

    logger.debug(f"Using auth token: '{auth_token}'")
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
    alert_type_str = f" ({alert_types})" if alert_types else ""
    return f"🚨 УВАГА! Тривога в **{region_name}**!{alert_type_str}\nПрямуйте до укриття!"

def format_no_alert_message(region_name: str) -> str:
    return f"✅ Відбій тривоги в **{region_name}**."

async def notify_user(context: ContextTypes.DEFAULT_TYPE, user_id: int, message: str) -> None:
    try:
        delay = float(config.cfg.get('NOTIFICATION_DELAY', 0.1))
        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode='Markdown',
            disable_notification=False
        )
        await asyncio.sleep(delay)
    except Exception as e:
        logger.error(f"Failed to notify user {user_id}: {e}")
        if isinstance(e, (Forbidden, BadRequest)):
            db.remove_subscriber(user_id)

async def check_air_raid_status(context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Checking air raid status...")
    current_status = await get_air_raid_status(context)
    if current_status is None:
        logger.error("Failed to fetch air raid status.")
        return

    bot_data = context.bot_data.setdefault('last_alert_status', {'data': [], 'lastUpdate': None})
    last_status = {region['regionId']: region for region in bot_data['data']}
    current_active_regions: Set[str] = {region['regionId'] for region in current_status if region.get('activeAlerts')}

    subscribers = db.get_subscribers()
    subscribers_dict: Dict[int, Set[Optional[str]]] = {}
    for user_id, region_id in subscribers:
        if not isinstance(region_id, (str, type(None))):
            logger.error(f"Invalid region_id type from database: {region_id} (type: {type(region_id)})")
            continue
        subscribers_dict.setdefault(user_id, set()).add(region_id)

    for user_id, regions in subscribers_dict.items():
        selected_region = context.user_data.get('selected_region') if user_id in context.user_data else None
        try:
            regions = regions if None not in regions else {None}
            for region_id in regions:
                if region_id is None or (selected_region and region_id == selected_region):
                    for region in current_status:
                        if region_id is not None and region['regionId'] != region_id:
                            continue
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
        except Exception as e:
            logger.error(f"Error notifying {user_id}: {e}", exc_info=True)
            await context.bot.send_message(chat_id=user_id, text=f"⚠️ Помилка: {str(e)}")

    bot_data['data'] = current_status
    bot_data['lastUpdate'] = datetime.now(ZoneInfo("UTC")).isoformat()

async def alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        current_alerts = await get_air_raid_status()
        if current_alerts is None:
            await update.message.reply_text("Не вдалося отримати статус тривог.")
            return

        selected_region = context.user_data.get('selected_region')
        active_regions = [
            region for region in current_alerts
            if region.get('activeAlerts') and (not selected_region or region['regionId'] == selected_region)
        ]
        if not active_regions:
            await update.message.reply_text("Наразі тривог немає в обраній області.")
        else:
            message = "🚨 *Активні тривоги:*\n\n"
            for region in active_regions:
                name = helpers.escape_markdown(region.get('regionName', 'Невідомий регіон'), version=2)
                alert_types = [ALERT_TYPES_TRANSLATION.get(a.get('type', 'Невідомо'), a.get('type', 'Невідомо')) 
                             for a in region.get('activeAlerts', [])]
                types_str = ", ".join(alert_types)
                message += f"\\- {name}: {types_str}\n"
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Помилка: {str(e)}")
        raise