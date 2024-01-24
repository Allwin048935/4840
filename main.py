# trading_bot.py

import ccxt
import pandas as pd
import numpy as np
import time
from config import BINANCE_API_KEY, BINANCE_API_SECRET, symbols, time_interval  # Import credentials and settings from config file

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
short_ema_period = 9
long_ema_period = 21

# Track the last order type placed for each symbol
last_order_types = {symbol: None for symbol in symbols}

# Function to fetch historical data for futures
def fetch_ohlcv(symbol, timeframe, limit):
    ohlcv = exchange.fapiPublic_get_klines({'symbol': symbol, 'interval': timeframe, 'limit': limit})
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

# Function to calculate EMA
def calculate_ema(df, period, column='close'):
    return df[column].ewm(span=period, adjust=False).mean()

# Main trading function for futures
def ema_strategy():
    while True:
        try:
            for symbol in symbols:
                # Fetch historical data for each symbol
                historical_data = fetch_ohlcv(symbol, time_interval, 100)

                # Fetch the latest candlestick for each symbol
                latest_candle = exchange.fapiPublic_ticker_24hr({'symbol': symbol})
                latest_close = float(latest_candle['lastPrice'])

                # Append the latest data to historical data
                historical_data = historical_data.append({'close': latest_close}, ignore_index=True)

                # Calculate EMAs
                historical_data['short_ema'] = calculate_ema(historical_data, short_ema_period)
                historical_data['long_ema'] = calculate_ema(historical_data, long_ema_period)

                # Make trading decisions for each symbol
                if historical_data['short_ema'].iloc[-1] > historical_data['long_ema'].iloc[-1] and last_order_types[symbol] != 'BUY':
                    print(f'{symbol} Buy Signal')
