import os
import logging
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)

cfg: Dict[str, Any] = {}

def validate_config(cfg: Dict[str, Any]) -> None:
    """
    Validates configuration values.

    Args:
        cfg: Configuration dictionary.

    Raises:
        ValueError: If required keys are missing or invalid.
    """
    errors = []

    # Validate BOT_TOKEN
    bot_token = cfg.get('BOT_TOKEN')
    if not bot_token or not re.match(r'^\d+:[\w-]{35}$', bot_token):
        errors.append("BOT_TOKEN is missing or has invalid format.")

    # Validate UKRAINE_ALARM_TOKEN
    alarm_token = cfg.get('UKRAINE_ALARM_TOKEN')
    if not alarm_token or not re.match(r'^[\w]{8}:[\w]{32}$', alarm_token):
        errors.append("UKRAINE_ALARM_TOKEN is missing or has invalid format.")

    # Validate WEATHER_API_KEY
    weather_key = cfg.get('WEATHER_API_KEY')
    if not weather_key or len(weather_key) < 30:
        errors.append("WEATHER_API_KEY is missing or too short.")

    # Validate AIR_RAID_CHECK_INTERVAL
    interval = cfg.get('AIR_RAID_CHECK_INTERVAL', 90)
    if not isinstance(interval, int) or interval < 30:
        cfg['AIR_RAID_CHECK_INTERVAL'] = 90
        logger.warning("AIR_RAID_CHECK_INTERVAL invalid or too small. Using default: 90.")

    # Validate NOTIFICATION_DELAY
    delay = cfg.get('NOTIFICATION_DELAY', 0.1)
    if not isinstance(delay, (int, float)) or delay < 0:
        cfg['NOTIFICATION_DELAY'] = 0.1
        logger.warning("NOTIFICATION_DELAY invalid or negative. Using default: 0.1.")

    # Validate ADMIN_IDS
    admin_ids = cfg.get('ADMIN_IDS', '')
    if admin_ids and not all(id.strip().isdigit() for id in admin_ids.split(',')):
        errors.append("ADMIN_IDS contains invalid user IDs.")

    if errors:
        raise ValueError("\n".join(errors))

def load_config() -> None:
    """
    Loads configuration from environment variables into global cfg dictionary.

    Raises:
        ValueError: If required parameters are missing or invalid.
    """
    global cfg

    config_keys_info = {
        'BOT_TOKEN': {'type': str, 'required': True},
        'ADMIN_IDS': {'type': str, 'required': False, 'default': ''},
        'WEATHER_API_KEY': {'type': str, 'required': True},
        'UKRAINE_ALARM_TOKEN': {'type': str, 'required': True},
        'AIR_RAID_API_URL': {'type': str, 'required': False, 'default': 'https://api.ukrainealarm.com/api/v3/alerts'},
        'AIR_RAID_CHECK_INTERVAL': {'type': int, 'required': False, 'default': 90},
        'NOTIFICATION_DELAY': {'type': float, 'required': False, 'default': 0.1}
    }

    for key, info in config_keys_info.items():
        env_value = os.environ.get(key)
        if env_value is not None:
            try:
                if info['type'] == int:
                    cfg[key] = int(env_value)
                elif info['type'] == float:
                    cfg[key] = float(env_value.replace(',', '.'))
                else:
                    cfg[key] = env_value
                logger.info(f"Loaded '{key}' from environment variable.")
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid value for {key}: {env_value}. Using default if available.")
        elif not info['required'] and 'default' in info:
            cfg[key] = info['default']
            logger.info(f"Using default value for '{key}': {info['default']}")

    missing_keys = [key for key, info in config_keys_info.items() if info['required'] and key not in cfg]
    if missing_keys:
        error_msg = f"Missing required configuration keys: {', '.join(missing_keys)}."
        logger.critical(error_msg)
        raise ValueError(error_msg)

    validate_config(cfg)
    logger.info("Configuration loaded and validated successfully.")