# config.py
import json
import os
import logging
from typing import Dict, Any, Optional

# Настройка логирования для этого модуля
logger = logging.getLogger(__name__)

# Глобальный словарь для хранения загруженной конфигурации
# Аннотация типа Dict[str, Any] означает словарь с ключами-строками и значениями любого типа
cfg: Dict[str, Any] = {}

# Имя файла конфигурации
CONFIG_FILE = 'config.json'

def load_config() -> None:
    """
    Загружает конфигурацию из файла config.json и переменных окружения.
    Значения из переменных окружения имеют приоритет над значениями из файла.
    Сохраняет результат в глобальный словарь `cfg`.
    Вызывает ValueError, если отсутствуют обязательные параметры.
    """
    global cfg # Объявляем, что будем изменять глобальную переменную cfg

    # 1. Чтение из файла config.json
    file_config: Dict[str, Any] = {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            file_config = json.load(f)
            logger.info(f"Configuration successfully loaded from {CONFIG_FILE}")
    except FileNotFoundError:
        logger.warning(f"Configuration file '{CONFIG_FILE}' not found. "
                       "Will rely on environment variables and defaults.")
        # Инициализируем пустым словарем, если файла нет
        file_config = {}
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {CONFIG_FILE}: {e}. Check its syntax.")
        # Пробрасываем ошибку, так как некорректный JSON - серьезная проблема
        raise ValueError(f"Invalid JSON in {CONFIG_FILE}") from e
    except Exception as e:
        logger.error(f"An unexpected error occurred while reading {CONFIG_FILE}: {e}")
        raise # Пробрасываем другие возможные ошибки чтения файла

    # Обновляем глобальный cfg данными из файла
    cfg.update(file_config)

    # 2. Чтение из переменных окружения (перезаписывают значения из файла)
    # Список ключей, которые будем искать в окружении и в JSON
    # Используем те же имена ключей, что и в JSON
    config_keys_info = {
        'BOT_TOKEN': {'type': str, 'required': True},
        'ADMIN_ID': {'type': str, 'required': True}, # Храним как строку, конвертируем в int в main.py
        'WEATHER_API_KEY': {'type': str, 'required': True},
        'UKRAINE_ALARM_TOKEN': {'type': str, 'required': True},
        'AIR_RAID_API_URL': {'type': str, 'required': False, 'default': 'https://api.ukrainealarm.com/api/v3/alerts'},
        'AIR_RAID_CHECK_INTERVAL': {'type': int, 'required': False, 'default': 90},
        'NOTIFICATION_DELAY': {'type': float, 'required': False, 'default': 0.1}
    }

    for key, info in config_keys_info.items():
        env_value_str: Optional[str] = os.environ.get(key)

        if env_value_str is not None:
            # Пытаемся преобразовать тип, если это не строка
            target_type = info['type']
            converted_value: Any = None
            conversion_ok = False

            if target_type == int:
                try:
                    converted_value = int(env_value_str)
                    conversion_ok = True
                except ValueError:
                    logger.warning(f"Environment variable {key}='{env_value_str}' is not a valid integer. "
                                   f"Using value from {CONFIG_FILE} if available, or default.")
            elif target_type == float:
                try:
                    # Заменяем запятую на точку для поддержки разных локалей
                    converted_value = float(env_value_str.replace(',', '.'))
                    conversion_ok = True
                except ValueError:
                     logger.warning(f"Environment variable {key}='{env_value_str}' is not a valid float. "
                                    f"Using value from {CONFIG_FILE} if available, or default.")
            else: # Для str и других типов просто берем значение
                converted_value = env_value_str
                conversion_ok = True

            if conversion_ok:
                cfg[key] = converted_value # Обновляем значение в cfg
                logger.info(f"Loaded '{key}' from environment variable.")
            # else: оставляем значение из файла (уже в cfg) или будет установлено значение по умолчанию ниже

    # 3. Установка значений по умолчанию (если не заданы ни в файле, ни в окружении)
    for key, info in config_keys_info.items():
        if key not in cfg and not info['required'] and 'default' in info:
            cfg[key] = info['default']
            logger.info(f"Using default value for '{key}': {info['default']}")

    # 4. Проверка наличия обязательных параметров
    missing_keys: list[str] = []
    for key, info in config_keys_info.items():
        if info['required'] and cfg.get(key) is None: # Проверяем на None или отсутствие
            missing_keys.append(key)

    if missing_keys:
         error_msg = (f"Missing required configuration keys: {', '.join(missing_keys)}. "
                      f"Please set them in {CONFIG_FILE} or as environment variables.")
         logger.critical(error_msg)
         raise ValueError(error_msg) # Вызываем исключение, останавливая запуск

    logger.info("Configuration loading complete.")
    # Не логируем сам cfg, так как он может содержать чувствительные данные (токены)
    # logger.debug(f"Final configuration: {cfg}")

# Не вызываем load_config() при импорте, пусть main.py это делает явно.
# load_config()