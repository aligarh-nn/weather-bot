import logging
import requests
from datetime import datetime, timedelta
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

# 🔐 ВСТАВЬ СЮДА СВОИ КЛЮЧИ
TELEGRAM_TOKEN = '8313163480:AAFfPfP488s6CU2wNRW7izYO5XgVzagIK_U'
OPENWEATHER_KEY = '5651fa2b774956bf6c11e9b3cee22651'
CHAT_ID = None  # получишь после /start

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_TOKEN)

def get_weather_forecast():
    url = f'https://api.openweathermap.org/data/2.5/forecast?q=Ryazan,RU&units=metric&lang=ru&appid={OPENWEATHER_KEY}'
    response = requests.get(url)
    data = response.json()
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d 12:00:00')
    forecast = next((item for item in data['list'] if item['dt_txt'] == tomorrow), None)

    if forecast:
        temp = forecast['main']['temp']
        description = forecast['weather'][0]['description']
        return f"🌤 Прогноз на завтра в Рязани:\nТемпература: {temp}°C\nПогода: {description}"
    else:
        return "Не удалось получить прогноз погоды."

async def start(update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    CHAT_ID = update.effective_chat.id
    await context.bot.send_message(chat_id=CHAT_ID, text="✅ Бот активен! Прогноз будет приходить каждый день в 8:00.")

def schedule_weather():
    forecast = get_weather_forecast()
    if CHAT_ID:
        bot.send_message(chat_id=CHAT_ID, text=forecast)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    scheduler = BackgroundScheduler(timezone=pytz.timezone('Europe/Moscow'))
    scheduler.add_job(schedule_weather, 'cron', hour=8, minute=0)
    scheduler.start()

    app.run_polling()
