import os
from binance.client import Client
from telegram import Bot, ParseMode
from telegram.ext import Updater, CommandHandler
import schedule
import time
from config import BINANCE_API_KEY, BINANCE_API_SECRET, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, SYMBOLS

# Binance API configuration
binance_client = Client(api_key=BINANCE_API_KEY, api_secret=BINANCE_API_SECRET)

# Telegram API configuration
telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Variable to store the last sent message
last_sent_message = ""

# Function to get open futures orders from Binance
def get_open_orders(context):
    global last_sent_message
    try:
        open_orders = binance_client.futures_get_open_orders()
        if open_orders:
            orders_text = "\n".join([f"{order['symbol']}: {order['side']} {order['type']} {order['origQty']} @ {order['price']}" for order in open_orders])
            new_message = f"Open Futures Orders:\n{orders_text}"

            # Check if the message has changed before sending
            if new_message != last_sent_message:
                telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=new_message, parse_mode=ParseMode.MARKDOWN)
                last_sent_message = new_message
        else:
            new_message = "No open orders."

            # Check if the message has changed before sending
            if new_message != last_sent_message:
                telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=new_message)
                last_sent_message = new_message
    except Exception as e:
        telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"Error: {str(e)}")

# Function to schedule the job
def schedule_job():
    job = schedule.every(1).minutes
    job.do(get_open_orders, context=None)

# Function to start the bot
def start_bot():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("get_open_orders", get_open_orders))

    updater.start_polling()

    # Schedule the job
    schedule_job()

    # Keep the program running
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    start_bot()

