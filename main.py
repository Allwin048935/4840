import ccxt
import pandas as pd
import time
from config import BINANCE_API_KEY, BINANCE_API_SECRET, symbols, time_interval

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
open_orders = {symbol: None for symbol in symbols}

# Define risk parameters
quantity = 100  # USDT
leverage = 10
limit_offset_percentage = 0.1  # 0.1% for both long and short

# Function to fetch historical data for futures
def fetch_ohlcv(symbol, timeframe, limit):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

# Function to calculate EMA
def calculate_ema(df, period, column='close'):
    return df[column].ewm(span=period, adjust=False).mean()

# Function to place a limit buy order
def place_limit_buy_order(symbol, quantity, price, leverage):
    try:
        order = exchange.create_limit_buy_order(
            symbol=symbol,
            quantity=quantity,
            price=price,
            leverage=leverage
        )
        print(f"Limit Buy Order placed for {symbol}: {order}")
        return order
    except Exception as e:
        print(f"Error placing Limit Buy Order for {symbol}: {e}")

# Function to place a limit sell order
def place_limit_sell_order(symbol, quantity, price, leverage):
    try:
        order = exchange.create_limit_sell_order(
            symbol=symbol,
            quantity=quantity,
            price=price,
            leverage=leverage
        )
        print(f"Limit Sell Order placed for {symbol}: {order}")
        return order
    except Exception as e:
        print(f"Error placing Limit Sell Order for {symbol}: {e}")

# Function to close open orders
def close_open_orders(symbol):
    try:
        if open_orders[symbol]:
            order_id = open_orders[symbol]['id']
            exchange.cancel_order(order_id, symbol=symbol)
            print(f"Cancelled open order for {symbol}: {order_id}")
    except Exception as e:
        print(f"Error cancelling open order for {symbol}: {e}")

# Main trading function for futures
def ema_strategy():
    while True:
        try:
            for symbol in symbols:
                # Fetch historical data for each symbol
                historical_data = fetch_ohlcv(symbol, time_interval, 100)

                # Fetch the latest candlestick for each symbol
                latest_candle = exchange.fetch_ticker(symbol)
                latest_close = float(latest_candle['close'])

                # Append the latest data to historical data
                historical_data = historical_data.append({'close': latest_close}, ignore_index=True)

                # Calculate EMAs
                historical_data['short_ema'] = calculate_ema(historical_data, short_ema_period)
                historical_data['long_ema'] = calculate_ema(historical_data, long_ema_period)

                # Make trading decisions for each symbol
                if historical_data['short_ema'].iloc[-1] > historical_data['long_ema'].iloc[-1] and last_order_types[symbol] != 'BUY':
                    print(f'{symbol} Buy Signal')
                    # Implement your buy logic here for futures
                    # For example, place a limit buy order with a price 0.1% below the current market price
                    limit_price = latest_close * (1 - limit_offset_percentage / 100)
                    close_open_orders(symbol)
                    open_orders[symbol] = place_limit_buy_order(symbol, quantity, limit_price, leverage)
                    last_order_types[symbol] = 'BUY'

                elif historical_data['short_ema'].iloc[-1] < historical_data['long_ema'].iloc[-1] and last_order_types[symbol] != 'SELL':
                    print(f'{symbol} Sell Signal')
                    # Implement your sell logic here for futures
                    # For example, place a limit sell order with a price 0.1% above the current market price
                    limit_price = latest_close * (1 + limit_offset_percentage / 100)
                    close_open_orders(symbol)
                    open_orders[symbol] = place_limit_sell_order(symbol, quantity, limit_price, leverage)
                    last_order_types[symbol] = 'SELL'

            # Sleep for some time (e.g., 5 minutes) before checking again
            time.sleep(300)

        except Exception as e:
            print(f'An error occurred: {e}')
            time.sleep(60)  # Wait for a minute before trying again

# Run the trading strategy
ema_strategy()

