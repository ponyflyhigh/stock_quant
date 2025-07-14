import json
import pandas as pd
from binance.client import Client
import matplotlib.pyplot as plt # Needed for font setting in main sometimes
import matplotlib as mpl
import time
# Import custom modules
from stock_quant.test_Bash.day_data import get_binance_klines, calculate_all_indicators
from strategy import Strategy
from backtester import Backtester
from result_plot import plot_results

# --- Load Configuration ---
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    print("Error: config.json not found. Please create it based on the template.")
    exit()
except json.JSONDecodeError:
    print("Error: config.json is not valid JSON. Please check its content.")
    exit()

# --- Binance API Setup ---
api_key = config['binance_api_key']
api_secret = config['binance_api_secret']
binance_client = Client(api_key, api_secret)

# --- General Settings ---
tokens = config['tokens']
interval = config['interval']
start_date = config['start_date']
end_date = config['end_date']
initial_capital = config['initial_capital']
commission_rate = config['commission_rate']
slippage_rate = config['slippage_rate']
data_path = config['data_path']

# --- Strategy Specific Settings ---
strategy_name = "macd" # You can change this to other strategies if implemented
strategy_params = config['strategy_params'].get(strategy_name, {})

# --- Font Settings for English (repeated for robustness) ---
mpl.rcParams['font.family'] = 'sans-serif'
mpl.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans', 'Liberation Sans', 'Bitstream Vera Sans']
mpl.rcParams['axes.unicode_minus'] = False

# --- Main Backtesting Loop ---
for token in tokens:
    print(f"\n--- Running backtest for {token} with {strategy_name.upper()} Strategy ---")

    # 1. Get Historical Data
    data = get_binance_klines(token, interval, start_date, end_date, binance_client, data_path)
    if data.empty:
        print(f"Skipping {token} due to data issues.")
        continue

    # Ensure data is sorted by index (time)
    data = data.sort_index()
    # Remove any NaN values that might result from early indicator calculations
    data = data.dropna()
    if data.empty:
        print(f"Skipping {token} as data became empty after dropping NaNs (likely due to short data period for indicator calculation).")
        continue

    # 2. Calculate Indicators
    data = calculate_all_indicators(data, strategy_name, strategy_params)
    data = data.dropna() # Drop rows with NaN from indicator calculation (e.g., beginning of MA)
    if data.empty:
        print(f"Skipping {token} as data became empty after dropping indicator NaNs.")
        continue

    # 3. Generate Signals
    strategy = Strategy(strategy_name, strategy_params)
    data_with_signals = strategy.generate_signals(data.copy()) # Use a copy to avoid modifying original data

    # 4. Run Backtest Simulation
    backtester = Backtester(initial_capital, commission_rate, slippage_rate)
    equity_curve, trades_df = backtester.run_backtest(data_with_signals)
    print(f"Trades DataFrame empty: {trades_df.empty}")
    print("Trades DataFrame head:")
    print(trades_df.head())
    # 5. Analyze Performance
    performance_metrics = backtester.analyze_performance(equity_curve, trades_df)

    # 6. Visualize Results
    if not equity_curve.empty:
        plot_results(equity_curve, data_with_signals, performance_metrics, token, strategy_name)
    else:
        print(f"No equity curve generated for {token}. Cannot plot results.")

    print(f"--- Backtest for {token} Finished ---")
    # Add a small delay between tokens to avoid hitting API rate limits
    time.sleep(2)