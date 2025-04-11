import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from air_raid import get_air_raid_status, format_alert_message, format_no_alert_message

@pytest.mark.asyncio
async def test_get_air_raid_status_success():
    mock_response = [
        {"regionId": "1", "regionName": "Київ", "activeAlerts": [{"type": "air_raid"}]},
    ]
    # Мокаем config.cfg с нужными значениями
    with patch('air_raid.config.cfg', {'AIR_RAID_API_URL': 'https://mock.url', 'UKRAINE_ALARM_TOKEN': 'mock_token'}):
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.headers = {'Last-Modified': '2023-01-01T00:00:00Z'}
            result = await get_air_raid_status()
            assert result == mock_response

@pytest.mark.asyncio
async def test_get_air_raid_status_not_modified():
    mock_context = AsyncMock()
    mock_context.bot_data = {
        'last_alert_status': {
            'data': [{"regionId": "1", "regionName": "Київ"}],
            'lastUpdate': '2023-01-01T00:00:00Z'
        }
    }
    # Мокаем config.cfg с нужными значениями
    with patch('air_raid.config.cfg', {'AIR_RAID_API_URL': 'https://mock.url', 'UKRAINE_ALARM_TOKEN': 'mock_token'}):
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 304
            result = await get_air_raid_status(mock_context)
            assert result == [{"regionId": "1", "regionName": "Київ"}]

def test_format_alert_message():
    assert format_alert_message("Київ", "air_raid") == "🚨 УВАГА! Повітряна тривога в **Київ**! (air_raid)\nПрямуйте до укриття!"
    assert format_alert_message("Львів") == "🚨 УВАГА! Повітряна тривога в **Львів**!\nПрямуйте до укриття!"

def test_format_no_alert_message():
    assert format_no_alert_message("Київ") == "✅ Відбій повітряної тривоги в **Київ**."