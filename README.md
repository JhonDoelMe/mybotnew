# Telegram Bot

A Telegram bot that provides currency rates, weather forecasts, and air raid alerts for Ukraine.

## Features
- **Currency Rates**: Displays USD/EUR rates from PrivatBank.
- **Weather**: Shows weather for any city (default: Kyiv) using OpenWeatherMap.
- **Air Raid Alerts**: Notifies about air raid alerts in Ukraine with region-specific subscriptions using UkraineAlarm API.
- **Commands**:
  - `/start`: Show main menu.
  - `/help`: Display help.
  - `/subscribe [region]`: Subscribe to air raid alerts.
  - `/unsubscribe [region]`: Unsubscribe.
  - `/status`: Check subscription status.
  - `/weather [city]`: Get weather.
  - `/alerts`: Show current alerts.
  - `/admin`: Admin stats (for authorized users).

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd <repository-directory>