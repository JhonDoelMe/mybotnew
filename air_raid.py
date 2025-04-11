# air_raid.py
import requests
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Set

import telegram
from telegram.ext import ContextTypes
from telegram.error import BadRequest, Forbidden

import database as db
import config # Импортируем модуль config для доступа к загруженным данным

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ключ для хранения последнего статуса в bot_data
LAST_STATUS_KEY = 'last_alert_status'

async def get_air_raid_status() -> Optional[List[Dict[str, Any]]]:
    """
    Запрашивает текущий статус воздушных тревог с API.

    Returns:
        Optional[List[Dict[str, Any]]]: Список активных тревог или None в случае ошибки.
    """
    api_url = config.cfg.get('AIR_RAID_API_URL')
    auth_token = config.cfg.get('UKRAINE_ALARM_TOKEN')

    if not api_url or not auth_token:
        logger.error("Air Raid API URL or Auth Token is not configured.")
        return None

    headers = {'Authorization': auth_token}
    try:
        response = requests.get(api_url, headers=headers, timeout=15) # Добавлен таймаут
        response.raise_for_status() # Проверка на HTTP ошибки (4xx, 5xx)

        # Дополнительная проверка статус кода, хотя raise_for_status() должна это покрыть
        if response.status_code == 200:
            try:
                # Используем response.json() для декодирования
                data = response.json()
                # Ожидаем список в ответе API v3
                if isinstance(data, list):
                    return data
                else:
                    logger.error(f"Air Raid API returned unexpected data type: {type(data)}. Expected list.")
                    return None
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON response from Air Raid API: {e}")
                logger.debug(f"Response text: {response.text}")
                return None
            except Exception as e:
                 logger.error(f"An unexpected error occurred during JSON processing: {e}")
                 return None
        else:
            # Эта часть может быть избыточной из-за raise_for_status, но для надежности оставим
            logger.error(f"Air Raid API request failed with status code {response.status_code}: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching air raid status: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred in get_air_raid_status: {e}")
        return None


def format_alert_message(region_name: str, alert_type: Optional[str] = None) -> str:
    """Форматирует сообщение о начале тревоги."""
    type_str = f" ({alert_type})" if alert_type else ""
    return f"🚨 УВАГА! Повітряна тривога в **{region_name}**!{type_str}\nПрямуйте до укриття!"

def format_no_alert_message(region_name: str) -> str:
    """Форматирует сообщение об отбое тревоги."""
    return f"✅ Відбій повітряної тривоги в **{region_name}**."

async def check_air_raid_status(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Проверяет статус воздушных тревог, сравнивает с предыдущим состоянием
    и отправляет уведомления подписчикам об изменениях.
    Использует context.bot_data для хранения состояния.
    """
    logger.info("Checking air raid status...")
    current_alerts_list = await get_air_raid_status()
    notification_delay = config.cfg.get('NOTIFICATION_DELAY', 0.1) # Получаем задержку из конфига

    if current_alerts_list is None:
        logger.warning("Could not fetch current air raid status. Skipping check.")
        return

    # Получаем предыдущий статус из bot_data. Инициализируем, если его нет.
    # Храним как словарь {region_id: alert_data} для быстрого доступа
    last_status: Dict[str, Dict[str, Any]] = context.bot_data.get(LAST_STATUS_KEY, {})
    current_status: Dict[str, Dict[str, Any]] = {}
    current_active_regions: Set[str] = set()

    # Обрабатываем текущие данные от API
    for alert_region in current_alerts_list:
        region_id = alert_region.get('regionId')
        if not region_id:
            logger.warning(f"Alert region missing 'regionId': {alert_region}")
            continue
        current_status[region_id] = alert_region
        # Если в регионе есть активные тревоги, добавляем его ID в сет
        if alert_region.get('activeAlerts'):
             current_active_regions.add(region_id)
        # Можно добавить более детальную проверку activeAlerts, если нужно отслеживать типы тревог
        # Например, сохранять set активных типов тревог для каждого региона

    # Определяем изменения статуса
    # Новые тревоги: регионы, которые активны сейчас, но не были активны (или не существовали) раньше
    new_alerts = current_active_regions - set(last_status.keys())
    # Отбои тревог: регионы, которые были активны раньше, но не активны сейчас
    ended_alerts = set(last_status.keys()) - current_active_regions

    # --- Логика для отслеживания изменения *типа* тревоги (если нужно) ---
    # changed_alerts = set()
    # for region_id in current_active_regions.intersection(set(last_status.keys())):
    #     # Сравниваем наборы активных тревог (если API дает детальную инфу по типам)
    #     last_active_types = {a['type'] for a in last_status[region_id].get('activeAlerts', [])}
    #     current_active_types = {a['type'] for a in current_status[region_id].get('activeAlerts', [])}
    #     if last_active_types != current_active_types:
    #         changed_alerts.add(region_id)
    # --------------------------------------------------------------------

    if not new_alerts and not ended_alerts: # and not changed_alerts:
        logger.info("No changes in air raid status.")
        # Обновляем статус в bot_data даже если нет изменений,
        # чтобы иметь актуальную временную метку 'lastUpdate' из API
        context.bot_data[LAST_STATUS_KEY] = current_status
        return

    logger.info(f"Changes detected - New alerts: {len(new_alerts)}, Ended alerts: {len(ended_alerts)}")

    # Получаем подписчиков
    subscribers = db.get_subscribers()
    if not subscribers:
        logger.info("No subscribers found. No notifications sent.")
        context.bot_data[LAST_STATUS_KEY] = current_status # Все равно обновляем статус
        return

    logger.info(f"Sending notifications to {len(subscribers)} subscribers...")

    # Отправка уведомлений
    tasks = []
    for user_id in subscribers:
        # Отправка уведомлений о новых тревогах
        for region_id in new_alerts:
            region_data = current_status.get(region_id)
            if region_data:
                region_name = region_data.get('regionName', 'Невідомий регіон')
                # Если есть информация о конкретных тревогах, можно взять тип первой
                alert_type = None
                active_alerts_in_region = region_data.get('activeAlerts', [])
                if active_alerts_in_region:
                    alert_type = active_alerts_in_region[0].get('type', 'Невідомий тип') # Пример
                message = format_alert_message(region_name, alert_type)
                tasks.append(context.bot.send_message(chat_id=user_id, text=message, parse_mode=telegram.constants.ParseMode.MARKDOWN_V2))
                await asyncio.sleep(notification_delay) # Задержка

        # Отправка уведомлений об отбое тревог
        for region_id in ended_alerts:
            region_data = last_status.get(region_id) # Берем имя из старого статуса
            if region_data:
                region_name = region_data.get('regionName', 'Невідомий регіон')
                message = format_no_alert_message(region_name)
                tasks.append(context.bot.send_message(chat_id=user_id, text=message, parse_mode=telegram.constants.ParseMode.MARKDOWN_V2))
                await asyncio.sleep(notification_delay) # Задержка

    # Выполняем отправку асинхронно и обрабатываем ошибки
    results = await asyncio.gather(*tasks, return_exceptions=True)

    success_count = 0
    fail_count = 0
    for i, result in enumerate(results):
         original_task = tasks[i] # Получаем доступ к аргументам задачи (например, chat_id)
         # Получаем chat_id из задачи (немного сложнее, т.к. он внутри вызова send_message)
         # В данном случае проще связать по индексу с циклом выше, если нужно знать user_id
         # target_user_id = subscribers[i // (len(new_alerts) + len(ended_alerts))] # Примерно так, но нужно точнее

         if isinstance(result, Exception):
             fail_count += 1
             # Определяем user_id, которому не удалось отправить
             # Это примерная логика, возможно, потребуется более точное отслеживание user_id для каждой задачи
             num_messages_per_user = len(new_alerts) + len(ended_alerts)
             if num_messages_per_user > 0:
                failed_user_index = i // num_messages_per_user
                if failed_user_index < len(subscribers):
                   failed_user_id = subscribers[failed_user_index]
                else:
                   failed_user_id = "unknown" # На всякий случай

             if isinstance(result, (BadRequest, Forbidden)):
                 logger.warning(f"Failed to send notification to user {failed_user_id}: {result}. User might have blocked the bot.")
                 # Здесь можно добавить логику удаления пользователя из БД, если ошибка Forbidden
                 if isinstance(result, Forbidden):
                     logger.info(f"Removing user {failed_user_id} due to Forbidden error.")
                     db.remove_subscriber(failed_user_id)
             else:
                 logger.error(f"Unexpected error sending notification to user {failed_user_id}: {result}")
         else:
             success_count += 1

    logger.info(f"Notifications sent. Success: {success_count}, Failed: {fail_count}")

    # Обновляем статус в bot_data после отправки
    context.bot_data[LAST_STATUS_KEY] = current_status
    logger.info("Air raid status check finished.")