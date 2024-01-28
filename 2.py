import ccxt
import pandas as pd
import time
from config import BINANCE_API_KEY, BINANCE_API_SECRET, symbols, time_interval, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from telegram import Bot
from telegram.constants import ParseMode

# Create a Binance Futures client
exchange = ccxt.binance({
    'apiKey': BINANCE_API_KEY,
    'secret': BINANCE_API_SECRET,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',  # Set the default type to futures
    }
})

# Define EMA strategy parameters
short_ema_period = 5
long_ema_period = 200

# Track the last order type placed for each symbol
last_order_types = {symbol: None for symbol in symbols}
open_orders = {symbol: None for symbol in symbols}

# Fixed quantity in USDT worth of contracts
fixed_quantity_usdt = 20

# Initialize Telegram bot
telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Function to send order info message to Telegram
def send_telegram_message(message):
    try:
        telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

# Function to fetch historical data for futures with EMA calculation
def fetch_ohlcv(symbol, timeframe, limit):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

    # Calculate short and long EMAs
    df['short_ema'] = calculate_ema(df, short_ema_period)
    df['long_ema'] = calculate_ema(df, long_ema_period)

    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

# Function to calculate EMA
def calculate_ema(df, period, column='close'):
    return df[column].ewm(span=period, adjust=False).mean()

# Modify your existing order placement functions to include Telegram alerts
def place_market_buy_order(symbol, quantity):
    try:
        order = exchange.create_market_buy_order(
            symbol=symbol,
            amount=quantity
        )
        message = f"Market Buy Order placed for {symbol}: {order}"
        print(message)
        send_telegram_message(message)
        return order
    except Exception as e:
        # Only print the error, not sending it to Telegram
        print(f"Error placing Market Buy Order for {symbol}: {e}")

# Function to place a market sell order
def place_market_sell_order(symbol, quantity):
    try:
        order = exchange.create_market_sell_order(
            symbol=symbol,
            amount=quantity
        )
        message = f"Market Sell Order placed for {symbol}: {order}"
        print(message)
        send_telegram_message(message)
        return order
    except Exception as e:
        # Only print the error, not sending it to Telegram
        print(f"Error placing Market Sell Order for {symbol}: {e}")

# Main trading function for futures
def ema_strategy():
    while True:
        try:
            for symbol in symbols:
                # Fetch historical data for each symbol
                historical_data = fetch_ohlcv(symbol, time_interval, 600)

                # Check if there's enough data for EMA calculation
                if len(historical_data) < long_ema_period:
                    print(f"Not enough data for {symbol}. Waiting for more data...")
                    continue

                # Fetch the latest candlestick for each symbol
                latest_candle = exchange.fetch_ticker(symbol)

                if 'close' not in latest_candle:
                    print(f"Error: 'close' not found in the latest_candle for {symbol}")
                    continue

                latest_close = latest_candle.get('close')

                # Check if latest_close is None or not a valid number
                if latest_close is None or not isinstance(latest_close, (int, float)):
                    print(f"Error: Invalid value for latest_close for {symbol}")
                    continue

                # Calculate the percentage change
                percentage_change = ((historical_data['short_ema'] - historical_data['long_ema']) / historical_data['long_ema']) * 100

                # Check if the percentage change is greater than or equal to the minimum condition
                min_percentage_condition = 0.2  # Adjust the threshold as needed

                print(f"Symbol: {symbol}, Latest Close: {latest_close}, Percentage Change: {percentage_change}")

                # Make trading decisions for each symbol
                if (
                    all(latest_close > historical_data['short_ema'].iloc[-1])
                    and all(latest_close < historical_data['long_ema'].iloc[-1])
                    and all(percentage_change >= abs(min_percentage_condition))
                ):
                    print(f'{symbol} Buy Signal (Crossover)')
                    open_orders[symbol] = place_market_buy_order(symbol, fixed_quantity_usdt)
                    last_order_types[symbol] = 'BUY'

                elif (
                    all(latest_close < historical_data['short_ema'].iloc[-1])
                    and all(latest_close > historical_data['long_ema'].iloc[-1])
                    and all(percentage_change >= abs(min_percentage_condition))
                ):
                    print(f'{symbol} Sell Signal (Crossunder)')
                    open_orders[symbol] = place_market_sell_order(symbol, fixed_quantity_usdt)
                    last_order_types[symbol] = 'SELL'

            # Sleep for some time (e.g., 5 minutes) before checking again
            time.sleep(300)

        except Exception as e:
            # Only print the error, not sending it to Telegram
            print(f'An error occurred: {e}')
            time.sleep(300)  # Wait for a minute before trying again

# Run the trading strategy
ema_strategy()
