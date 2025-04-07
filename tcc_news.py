# tcc_news.py
import json
import os
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")

CONFIG_FILE = 'config.json'
PROCESSED_NEWS = set()  # Множество для хранения текстов уже обработанных новостей

# Клавиатура модуля "Новости ТЦК"
tcc_news_keyboard = [['Получить последние новости'], ['Вернуться в главное меню']]
tcc_news_reply_markup = ReplyKeyboardMarkup(tcc_news_keyboard, resize_keyboard=True)

def show_tcc_news_menu(update: Update, context: CallbackContext) -> None:
    """Отправляет меню новостей ТЦК."""
    update.message.reply_text("Выберите действие:", reply_markup=tcc_news_reply_markup)

async def get_channel_messages(client, channel_id, since_date):
    """Получает сообщения из указанного канала, начиная с определенной даты."""
    try:
        channel = await client.get_entity(channel_id)
        all_messages = []
        async for message in client.iter_messages(channel, limit=None, reverse=True, from_date=since_date):
            all_messages.append(message)
        return all_messages
    except Exception as e:
        print(f"Ошибка при получении сообщений из канала {channel_id}: {e}")
        return []

def get_tcc_news(update: Update, context: CallbackContext) -> None:
    """Получает и отправляет последние новости ТЦК из каналов за последние три дня."""
    async def main():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)

            target_chat_id = config.get('target_chat_id')
            telegram_channels = config.get('telegram_channels', [])

            if not target_chat_id or not telegram_channels:
                update.message.reply_text("Некорректно настроен файл конфигурации.")
                return

            if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
                update.message.reply_text("Не найдены TELEGRAM_API_ID или TELEGRAM_API_HASH в файле .env.")
                return

            client = TelegramClient('session_name', int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
            await client.connect()

            if not await client.is_connected():
                update.message.reply_text("Не удалось подключиться к Telegram.")
                return

            three_days_ago = datetime.now() - timedelta(days=3)
            found_news = []

            for channel_info in telegram_channels:
                channel_id = channel_info.get('channel_id')
                keywords = channel_info.get('keywords', [])
                if channel_id and keywords:
                    messages = await get_channel_messages(client, channel_id, three_days_ago)
                    for message in messages:
                        if message.text:
                            for keyword in keywords:
                                if keyword.lower() in message.text.lower() and message.text not in PROCESSED_NEWS:
                                    found_news.append(f"Источник: {channel_id}\n{message.text}\n\n")
                                    PROCESSED_NEWS.add(message.text) # Добавляем новость в множество обработанных
                                    break # Переходим к следующему сообщению, если ключевое слово найдено

            await client.disconnect()

            if found_news:
                news_text = "📰 Последние новости ТЦК за три дня:\n\n" + "\n".join(found_news)
                try:
                    await context.bot.send_message(chat_id=target_chat_id, text=news_text)
                    update.message.reply_text("Новости ТЦК успешно получены и отправлены.")
                except Exception as e:
                    update.message.reply_text(f"Ошибка при отправке новостей: {e}")
            else:
                update.message.reply_text("Свежих новостей ТЦК по заданным ключевым словам за последние три дня не найдено.")

        except FileNotFoundError:
            update.message.reply_text("Файл конфигурации 'config.json' не найден.")
        except json.JSONDecodeError:
            update.message.reply_text("Ошибка при чтении файла конфигурации 'config.json'.")
        except Exception as e:
            update.message.reply_text(f"Произошла непредвиденная ошибка при получении новостей ТЦК: {e}")

    import asyncio
    asyncio.run(main())