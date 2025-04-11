# Telegram Бот Помощник (Украина)

Этот Telegram-бот предоставляет полезную информацию для пользователей в Украине:
* Курсы валют (ПриватБанк, наличный)
* Прогноз погоды (OpenWeatherMap)
* Статус воздушных тревог по областям (на основе API UkraineAlarm)
* Уведомления о начале и отбое воздушных тревог (по подписке)

## Возможности

* **Курсы валют**: Отображение текущего курса покупки/продажи USD и EUR.
* **Погода**: Получение прогноза погоды для указанного города (или Киева по умолчанию).
* **Статус тревог**: Проверка текущего статуса воздушных тревог по всем областям Украины по запросу.
* **Подписка на уведомления**: Пользователи могут подписаться, чтобы получать мгновенные уведомления о начале и отбое воздушных тревог во всех областях.
* **Команды администратора**: Базовые команды для администратора (например, проверка количества подписчиков).

## Установка и настройка

1.  **Клонируйте репозиторий:**
    ```bash
    git clone <url-вашего-репозитория>
    cd mybotnew
    ```

2.  **Создайте и активируйте виртуальное окружение:**
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # MacOS/Linux
    source venv/bin/activate
    ```

3.  **Установите зависимости:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Настройте конфигурацию:**

    * Создайте файл `.env` в корневой папке проекта (рядом с `main.py`) и добавьте туда ваш токен бота:
        ```dotenv
        BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
        ```
        *(Значение токена из `.env` будет иметь приоритет над значением в `config.json`)*

    * Отредактируйте файл `config.json`, указав необходимые токены и ID:
        ```json
        {
          "BOT_TOKEN": "YOUR_BOT_TOKEN_HERE", // Обязательно. Получить у @BotFather в Telegram
          "ADMIN_ID": "YOUR_ADMIN_ID_HERE", // Обязательно. Ваш Telegram User ID (можно узнать у @userinfobot)
          "WEATHER_API_KEY": "YOUR_OPENWEATHERMAP_API_KEY_HERE", // Обязательно. Получить на [https://openweathermap.org/](https://openweathermap.org/)
          "UKRAINE_ALARM_TOKEN": "YOUR_UKRAINEALARM_API_TOKEN_HERE", // Обязательно. Получить на [https://api.ukrainealarm.com/](https://api.ukrainealarm.com/) (нужна регистрация)
          "AIR_RAID_API_URL": "[https://api.ukrainealarm.com/api/v3/alerts](https://api.ukrainealarm.com/api/v3/alerts)", // URL API тревог (обычно менять не нужно)
          "AIR_RAID_CHECK_INTERVAL": 90, // Интервал проверки тревог в секундах (например, 90)
          "NOTIFICATION_DELAY": 0.1 // Задержка между отправкой уведомлений подписчикам в секундах (например, 0.1)
        }
        ```
    * **Где получить ключи:**
        * `BOT_TOKEN`: Создайте бота через `@BotFather` в Telegram.
        * `ADMIN_ID`: Узнайте свой ID с помощью ботов вроде `@userinfobot`.
        * `WEATHER_API_KEY`: Зарегистрируйтесь на [OpenWeatherMap](https://openweathermap.org/) и получите API ключ (бесплатного тарифа обычно достаточно).
        * `UKRAINE_ALARM_TOKEN`: Зарегистрируйтесь на [сайте API UkraineAlarm](https://api.ukrainealarm.com/) и получите токен доступа.

## Запуск бота

Активируйте ваше виртуальное окружение (если еще не активно) и выполните:

```bash
python main.py