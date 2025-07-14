import pandas as pd
from binance.client import Client
from binance.enums import HistoricalKlinesType
import datetime
import os
import ta # Technical Analysis library

def get_binance_klines(symbol, interval, start_str, end_str, client, data_path="data/"):
    """
    从币安获取历史 K 线数据并保存到 CSV。
    symbol: 交易对，如 'BTCUSDT'
    interval: K 线周期，如 Client.KLINE_INTERVAL_1DAY
    start_str: 开始日期字符串，如 '1 Jan, 2023'
    end_str: 结束日期字符串，如 '31 Dec, 2023'
    client: 币安 API 客户端实例
    data_path: 数据保存路径
    """
    os.makedirs(data_path, exist_ok=True)
    file_path = os.path.join(data_path, f"{symbol}_{interval}.csv")

    if os.path.exists(file_path):
        print(f"Loading data for {symbol} from {file_path}")
        df = pd.read_csv(file_path, index_col='Open Time', parse_dates=True)
        # 检查数据是否完整，如果不完整或者需要更新，可以考虑重新下载
        if df.index.min() <= pd.to_datetime(start_str) and df.index.max() >= pd.to_datetime(end_str):
            return df
        else:
            print(f"Data for {symbol} in {file_path} is not complete for the requested period. Downloading again.")

    print(f"Downloading data for {symbol} from Binance...")
    try:
        klines = client.get_historical_klines(
            symbol,
            interval,
            start_str,
            end_str,
            klines_type=HistoricalKlinesType.FUTURES # Prefer futures for wider availability
        )
        if not klines: # Fallback to SPOT if futures data not found or empty
            print(f"No Futures data for {symbol}, trying Spot data...")
            klines = client.get_historical_klines(
                symbol,
                interval,
                start_str,
                end_str
            )
            
        if not klines:
            print(f"Could not retrieve historical data for {symbol}.")
            return pd.DataFrame()

        df = pd.DataFrame(klines, columns=[
            'Open Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close Time',
            'Quote Asset Volume', 'Number of Trades', 'Taker Buy Base Asset Volume',
            'Taker Buy Quote Asset Volume', 'Ignore'
        ])

        df['Open Time'] = pd.to_datetime(df['Open Time'], unit='ms')
        df['Close Time'] = pd.to_datetime(df['Close Time'], unit='ms')
        df[['Open', 'High', 'Low', 'Close', 'Volume']] = df[['Open', 'High', 'Low', 'Close', 'Volume']].astype(float)
        df = df.set_index('Open Time')
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        df.rename(columns={'Close': 'Close Price'}, inplace=True)
        df.to_csv(file_path) # Save to CSV for future use
        print(f"Data for {symbol} saved to {file_path}")
        return df
    except Exception as e:
        print(f"Error fetching {symbol} data from Binance: {e}")
        return pd.DataFrame()



if __name__ == "__main__":
    import os
    import pandas as pd
    from binance.client import Client
    from binance.enums import HistoricalKlinesType
    
    # 请替换为你的币安API密钥
    api_key = 'YOUR_API_KEY'
    api_secret = 'YOUR_API_SECRET'
    
    # 创建币安API客户端实例
    client = Client(api_key, api_secret)
    
    # 定义要获取数据的加密货币列表（USDT交易对）
    symbols = [
        'BTCUSDT',  # 比特币
        'ETHUSDT',  # 以太坊
        'SOLUSDT',  # 索拉纳
        'DOGEUSDT', # 狗狗币
        'SUIUSDT',  # Sui
        'ADAUSDT',  # 卡尔达诺
        'DOTUSDT',  # 波卡
        'XRPUSDT',  # 瑞波币
        'LTCUSDT',  # 莱特币
        'ONDOUSDT'  # 雪崩币
    ]
    
    # 定义K线周期（1天）
    interval = '4h'
    
    # 定义数据时间段
    start_str = '1 Jan, 2018'
    end_str = '31 Dec, 2025'
    
    # 定义数据保存路径
    data_path = "data/4hour"
    
    # 循环获取每种加密货币的数据
    for symbol in symbols:
        df = get_binance_klines(symbol, interval, start_str, end_str, client, data_path)
        if not df.empty:
            print(f"\n成功获取 {symbol} 的数据:")
            print(f"数据范围: {df.index.min()} 到 {df.index.max()}")
            print(f"数据行数: {len(df)}\n")
        else:
            print(f"\n获取 {symbol} 的数据失败\n")