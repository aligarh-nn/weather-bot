import logging
import requests
from datetime import datetime, timedelta, time as dtime
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackContext

TELEGRAM_TOKEN = "8313163480:AAFfPfP488s6CU2wNRW7izYO5XgVzagIK_U"
OPENWEATHER_API_KEY = "5651fa2b774956bf6c11e9b3cee22651"

logging.basicConfig(level=logging.INFO)

SUBSCRIBERS_FILE = "subscribers.txt"

def save_subscriber(chat_id: int):
    try:
        with open(SUBSCRIBERS_FILE, "a") as f:
            f.write(f"{chat_id}\n")
    except Exception as e:
        logging.error(f"Ошибка сохранения подписчика: {e}")

def load_subscribers():
    try:
        with open(SUBSCRIBERS_FILE, "r") as f:
            return set(int(line.strip()) for line in f if line.strip().isdigit())
    except FileNotFoundError:
        return set()
    except Exception as e:
        logging.error(f"Ошибка загрузки подписчиков: {e}")
        return set()

def get_weather(city="Рязань"):
    try:
        url_current = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
        )
        current = requests.get(url_current).json()

        if current.get("cod") != 200:
            return f"Ошибка: {current.get('message', 'Не удалось получить данные о погоде')}"

        temp = current["main"]["temp"]
        feels_like = current["main"]["feels_like"]
        description = current["weather"][0]["description"].capitalize()
        humidity = current["main"]["humidity"]

        lat = current["coord"]["lat"]
        lon = current["coord"]["lon"]

        url_forecast = (
            f"https://api.openweathermap.org/data/2.5/forecast"
            f"?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
        )
        forecast_data = requests.get(url_forecast).json()

        if forecast_data.get("cod") != "200":
            return f"Ошибка получения прогноза: {forecast_data.get('message', '')}"

        now = datetime.utcnow()
        next_day = (now + timedelta(days=1)).date()

        rain_hours = []
        for item in forecast_data["list"]:
            dt_txt = item["dt_txt"]
            dt_obj = datetime.strptime(dt_txt, "%Y-%m-%d %H:%M:%S")
            date_only = dt_obj.date()

            if date_only == next_day:
                pop = item.get("pop", 0)
                rain = item.get("rain", {}).get("3h", 0)

                if pop >= 0.5 and rain > 0.2:
                    time_str = dt_obj.strftime("%H:%M")
                    rain_hours.append(f"{time_str} — дождь ({rain:.1f} мм, вероятность {int(pop*100)}%)")

        rain_info = "\n".join(rain_hours) if rain_hours else "Дождя на следующий день не ожидается."

        return (
            f"🌦 Погода в {city}:\n"
            f"{description}, {temp}°C (ощущается как {feels_like}°C)\n"
            f"Влажность: {humidity}%\n\n"
            f"☔ Прогноз дождя на следующий день ({next_day}):\n"
            f"{rain_info}"
        )
    except Exception as e:
        return f"⚠️ Ошибка при получении погоды: {e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers = load_subscribers()
    if chat_id not in subscribers:
        save_subscriber(chat_id)
    await update.message.reply_text("Привет! Напиши /pogoda или /pogoda [город], чтобы узнать погоду.")

async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = "Рязань"
    if context.args:
        city = " ".join(context.args)
    text = get_weather(city)
    await update.message.reply_text(text)

async def daily_weather_sender(app):
    while True:
        now = datetime.utcnow()
        target_time = datetime.combine(now.date(), dtime(hour=11, minute=0))  # 14:00 по Москве = 11:00 UTC (летом)
        if now > target_time:
            target_time += timedelta(days=1)
        wait_seconds = (target_time - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        subscribers = load_subscribers()
        for chat_id in subscribers:
            try:
                text = get_weather("Рязань")
                await app.bot.send_message(chat_id=chat_id, text=f"Автоматический прогноз погоды на завтра:\n\n{text}")
            except Exception as e:
                logging.error(f"Ошибка отправки прогноза пользователю {chat_id}: {e}")

        # Ждем еще сутки
        await asyncio.sleep(24 * 3600 - wait_seconds)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pogoda", weather))

    # Запуск задачи по ежедневной рассылке прогноза
    app.job_queue.run_repeating(lambda ctx: asyncio.create_task(daily_weather_sender(app)), interval=24*3600, first=1)

    app.run_polling()
