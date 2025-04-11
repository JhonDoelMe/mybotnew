# tests/conftest.py
import pytest
from air_raid import config

@pytest.fixture(autouse=True)
def mock_config():
    config.cfg = {
        'AIR_RAID_API_URL': 'https://mock.url',
        'UKRAINE_ALARM_TOKEN': 'mock_token'
    }
    yield
    config.cfg = {}