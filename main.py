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

# Fixed quantity in USDT worth of contracts
fixed_quantity_usdt = 100

# Define risk parameters
limit_offset_percentage = 0.1  # 0.1% for both long and short
take_profit_percentage = 1.0  # 1% take profit

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

# Function to place a market buy order
def place_market_buy_order(symbol, quantity):
    try:
        order = exchange.create_market_buy_order(
            symbol=symbol,
            amount=fixed_quantity_usdt/price
        )
        print(f"Market Buy Order placed for {symbol}: {order}")
        return order
    except Exception as e:
        print(f"Error placing Market Buy Order for {symbol}: {e}")

# Function to place a market sell order
def place_market_sell_order(symbol, quantity):
    try:
        order = exchange.create_market_sell_order(
            symbol=symbol,
            amount=fixed_quantity_usdt/price
        )
        print(f"Market Sell Order placed for {symbol}: {order}")
        return order
    except Exception as e:
        print(f"Error placing Market Sell Order for {symbol}: {e}")

# Function to close open positions
def close_open_position(symbol):
    try:
        if open_orders[symbol]:
            position = exchange.fetch_position(symbol)
            if position['side'] == 'long':
                close_price = float(position['entryPrice']) * (1 + take_profit_percentage / 100)
                order = place_market_sell_order(symbol, position['positionAmt'])
                print(f"Closing open position for {symbol} with take profit: {order}")
            elif position['side'] == 'short':
                close_price = float(position['entryPrice']) * (1 - take_profit_percentage / 100)
                order = place_market_buy_order(symbol, position['positionAmt'])
                print(f"Closing open position for {symbol} with take profit: {order}")
    except Exception as e:
        print(f"Error closing open position for {symbol}: {e}")

# Function to close open orders
def close_open_orders(symbol):
    try:
        if open_orders[symbol]:
            exchange.cancel_order(open_orders[symbol]['id'], symbol=symbol)
            print(f"Cancelled open order for {symbol}: {open_orders[symbol]['id']}")
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

                # Calculate the quantity based on the fixed USDT value
                quantity = fixed_quantity_usdt / latest_close

                # Make trading decisions for each symbol
                if historical_data['short_ema'].iloc[-1] > historical_data['long_ema'].iloc[-1] and last_order_types[symbol] != 'BUY':
                    print(f'{symbol} Buy Signal')
                    # Implement your buy logic here for futures
                    # For example, place a market buy order
                    close_open_position(symbol)
                    close_open_orders(symbol)
                    open_orders[symbol] = place_market_buy_order(symbol, quantity)
                    last_order_types[symbol] = 'BUY'

                elif historical_data['short_ema'].iloc[-1] < historical_data['long_ema'].iloc[-1] and last_order_types[symbol] != 'SELL':
                    print(f'{symbol} Sell Signal')
                    # Implement your sell logic here for futures
                    # For example, place a market sell order
                    close_open_position(symbol)
                    close_open_orders(symbol)
                    open_orders[symbol] = place_market_sell_order(symbol, quantity)
                    last_order_types[symbol] = 'SELL'

            # Sleep for some time (e.g., 5 minutes) before checking again
            time.sleep(300)

        except Exception as e:
            print(f'An error occurred: {e}')
            time.sleep(60)  # Wait for a minute before trying again

# Run the trading strategy
ema_strategy()
