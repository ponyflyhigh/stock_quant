import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import matplotlib as mpl

def plot_results(equity_curve, data_with_signals, performance_metrics, token, strategy_name):
    """
    绘制回测结果和策略信号。
    equity_curve: 资金曲线 Series
    data_with_signals: 包含价格和信号的 DataFrame
    performance_metrics: 绩效指标字典
    token: 交易对名称
    strategy_name: 策略名称
    """
    # 确保使用英文友好字体
    mpl.rcParams['font.family'] = 'sans-serif'
    mpl.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans', 'Liberation Sans', 'Bitstream Vera Sans']
    mpl.rcParams['axes.unicode_minus'] = False

    sns.set_style("whitegrid")
    plt.style.use("seaborn-v0_8-darkgrid")

    # --- Plot 1: Equity Curve ---
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), sharex=True, gridspec_kw={'height_ratios': [2, 1]})

    ax1.plot(equity_curve.index, equity_curve, label='Equity Curve', color='purple', linewidth=2)
    ax1.set_title(f'{token} - {strategy_name.upper()} Strategy Equity Curve', fontsize=18)
    ax1.set_ylabel('Portfolio Value (USD)', fontsize=14)
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.legend(loc='upper left', fontsize=12)

    # Plot drawdown below equity curve
    peak = equity_curve.expanding(min_periods=1).max()
    drawdown = (equity_curve - peak) / peak
    ax2.fill_between(drawdown.index, drawdown, color='red', alpha=0.3)
    ax2.set_title('Drawdown', fontsize=16)
    ax2.set_xlabel('Date', fontsize=14)
    ax2.set_ylabel('Drawdown (%)', fontsize=14)
    ax2.tick_params(axis='x', rotation=45)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y*100:.0f}%')) # Format to percentage
    ax2.grid(True, linestyle='--', alpha=0.7)


    plt.tight_layout()
    plt.show()

    # --- Plot 2: Price and Signals ---
    plt.figure(figsize=(16, 8))
    sns.lineplot(data=data_with_signals['Close Price'], label='Close Price', color='blue', linewidth=1.5)
    
    # Check if MACD lines exist to plot them
    if 'MACD' in data_with_signals.columns and 'MACD_Signal' in data_with_signals.columns:
        sns.lineplot(data=data_with_signals['MACD'], label='MACD', color='orange', linewidth=1)
        sns.lineplot(data=data_with_signals['MACD_Signal'], label='MACD Signal Line', color='green', linewidth=1)

    # Identify buy/sell points from position changes (data['Signal'].diff())
    # Assuming `data_with_signals['Signal']` is the daily position (1: long, -1: short, 0: flat)
    # To plot actual trade points, we need to find where signal changes
    # For this backtester, 'Signal' is the position, so actual trades happen when position changes
    # Let's derive trade points from `trades_df` if available, or just plot `Signal` changes
    
    # If using the backtester's trade log, we can plot precise trade points
    # For simplicity here, we'll plot based on changes in `data_with_signals['Signal']` itself.
    # Note: the backtester logs actual trades, which is more accurate.
    # To use `trades_df` here, it would need to be passed from `main.py`
    
    # For now, let's derive from signal changes for visual consistency with price chart
    data_with_signals['Trade_Point'] = data_with_signals['Signal'].diff()
    
    buy_signals_plot = data_with_signals[data_with_signals['Trade_Point'] == 1]
    sell_signals_plot = data_with_signals[data_with_signals['Trade_Point'] == -1]

    plt.scatter(buy_signals_plot.index,
                data_with_signals['Close Price'].loc[buy_signals_plot.index],
                marker='^', color='green', s=150, label='Buy Signal', alpha=1, zorder=5)

    plt.scatter(sell_signals_plot.index,
                data_with_signals['Close Price'].loc[sell_signals_plot.index],
                marker='v', color='red', s=150, label='Sell Signal', alpha=1, zorder=5)


    plt.title(f'{token} - {strategy_name.upper()} Strategy Signals on Price Chart', fontsize=18)
    plt.xlabel('Date', fontsize=14)
    plt.ylabel('Price', fontsize=14)
    plt.legend(loc='upper left', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.show()

    # --- Print Performance Metrics ---
    print("\n--- Performance Metrics ---")
    for key, value in performance_metrics.items():
        print(f"{key}: {value}")