
# %% [markdown]
# # 基于MACD策略的主流加密货币回测分析
# 本分析使用币安公开API抓取历史K线数据，计算MACD指标，并进行策略回测，最后使用Seaborn可视化各币种近几年的累计收益率。

# %%
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import time

# 设置中文支持
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

sns.set(style="whitegrid")

# %%
def fetch_binance_klines(symbol, interval, start_str, limit=1000):
    url = "https://api.binance.com/api/v3/klines"
    start_ts = int(pd.to_datetime(start_str).timestamp() * 1000)
    all_klines = []

    while True:
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': start_ts,
            'limit': limit
        }
        resp = requests.get(url, params=params)
        data = resp.json()

        if not data:
            break
        all_klines.extend(data)

        last_time = data[-1][0]
        start_ts = last_time + 1

        if len(data) < limit:
            break
        time.sleep(0.5)

    df = pd.DataFrame(all_klines, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "num_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    df['close'] = df['close'].astype(float)
    return df[['open_time', 'close']].set_index('open_time')

# %%
def compute_macd(df, fast=12, slow=26, signal=9):
    df['ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
    df['macd'] = df['ema_fast'] - df['ema_slow']
    df['signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
    return df

# %%
def generate_signals(df):
    df['signal_flag'] = 0
    df.loc[(df['macd'].shift(1) < df['signal'].shift(1)) & (df['macd'] > df['signal']), 'signal_flag'] = 1
    df.loc[(df['macd'].shift(1) > df['signal'].shift(1)) & (df['macd'] < df['signal']), 'signal_flag'] = -1
    return df

# %%
def backtest(df, initial_cash=10000):
    cash = initial_cash
    position = 0
    equity_list = []

    for i in range(len(df)):
        signal = df['signal_flag'].iloc[i]
        price = df['close'].iloc[i]

        if signal == 1 and cash > 0:
            position = cash / price
            cash = 0
        elif signal == -1 and position > 0:
            cash = position * price
            position = 0

        equity = cash + position * price
        equity_list.append(equity)

    df['equity'] = equity_list
    df['returns'] = df['equity'].pct_change().fillna(0)
    return df

# %%
def plot_returns(dfs, title="MACD策略累计收益率"):
    plt.figure(figsize=(14, 7))
    combined = pd.DataFrame()
    for symbol, df in dfs.items():
        tmp = pd.DataFrame({
            '时间': df.index,
            '累计收益率': df['returns'].cumsum(),
            '币种': symbol
        })
        combined = pd.concat([combined, tmp], ignore_index=True)
    sns.lineplot(data=combined, x='时间', y='累计收益率', hue='币种')
    plt.title(title)
    plt.xlabel("时间")
    plt.ylabel("累计收益率")
    plt.legend()
    plt.tight_layout()
    plt.show()

# %%
# 主流币种分析入口（可自行扩展更多币种）
start_date = '2020-07-01'  # 三年数据
symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT', 'XRPUSDT']

dfs = {}
for sym in symbols:
    print(f"正在抓取 {sym} 历史数据...")
    df = fetch_binance_klines(sym, '1d', start_date)
    df = compute_macd(df)
    df = generate_signals(df)
    df = backtest(df)
    dfs[sym] = df

plot_returns(dfs)
