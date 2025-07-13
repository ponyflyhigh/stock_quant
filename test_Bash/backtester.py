import pandas as pd
import numpy as np
import datetime

class Backtester:
    def __init__(self, initial_capital, commission_rate, slippage_rate):
        self.initial_capital = float(initial_capital)
        self.commission_rate = float(commission_rate)
        self.slippage_rate = float(slippage_rate)
        self.portfolio = {
            'cash': self.initial_capital,
            'assets': 0 # 持有的资产数量
        }
        self.trades = [] # 记录每次交易
        self.equity_curve = pd.Series(dtype=float) # 资金曲线

    def run_backtest(self, data):
        """
        执行回测模拟。
        data: 包含 'Close Price' 和 'Signal' 的 DataFrame
        """
        current_position = 0 # -1: 空仓, 0: 无仓位, 1: 多仓

        for i, row in data.iterrows():
            current_price = row['Close Price']
            signal = row['Signal']
            
            # 记录每日总资产
            self.equity_curve.loc[i] = self.portfolio['cash'] + self.portfolio['assets'] * current_price

            # 交易逻辑
            if signal == 1 and current_position <= 0: # 买入信号且当前不是多头 (空仓或无仓位)
                # 计算可用于交易的资金，考虑避免借钱
                available_cash = self.portfolio['cash']
                if available_cash <= 0:
                    continue # 没有钱不能买

                # 模拟买入
                trade_amount_usd = available_cash * (1 - self.slippage_rate) # 考虑滑点
                amount_to_buy = trade_amount_usd / current_price
                commission = amount_to_buy * current_price * self.commission_rate # 买入佣金

                if self.portfolio['cash'] >= (amount_to_buy * current_price + commission):
                    self.portfolio['cash'] -= (amount_to_buy * current_price + commission)
                    self.portfolio['assets'] += amount_to_buy
                    self.trades.append({
                        'Date': i,
                        'Type': 'BUY',
                        'Price': current_price,
                        'Amount': amount_to_buy,
                        'Commission': commission,
                        'Cash_After_Trade': self.portfolio['cash'],
                        'Assets_After_Trade': self.portfolio['assets']
                    })
                    current_position = 1 # 转为多仓

            elif signal == -1 and current_position >= 0: # 卖出信号且当前不是空头 (多仓或无仓位)
                # 模拟卖出
                if self.portfolio['assets'] > 0: # 只有有多头仓位才能卖出
                    amount_to_sell = self.portfolio['assets']
                    commission = amount_to_sell * current_price * self.commission_rate # 卖出佣金
                    
                    self.portfolio['cash'] += (amount_to_sell * current_price * (1 - self.slippage_rate) - commission) # 考虑滑点
                    self.portfolio['assets'] = 0 # 清仓
                    self.trades.append({
                        'Date': i,
                        'Type': 'SELL',
                        'Price': current_price,
                        'Amount': amount_to_sell,
                        'Commission': commission,
                        'Cash_After_Trade': self.portfolio['cash'],
                        'Assets_After_Trade': self.portfolio['assets']
                    })
                    current_position = -1 # 转为空仓 (这里简单处理为空仓，不涉及卖空)
                else: # 如果是无仓位，卖出信号不操作
                    current_position = -1 # 也记录为无仓位，等待买入信号

        # 策略结束时清仓
        if self.portfolio['assets'] > 0:
            final_price = data['Close Price'].iloc[-1]
            amount_to_sell = self.portfolio['assets']
            commission = amount_to_sell * final_price * self.commission_rate
            self.portfolio['cash'] += (amount_to_sell * final_price * (1 - self.slippage_rate) - commission)
            self.portfolio['assets'] = 0
            self.trades.append({
                'Date': data.index[-1],
                'Type': 'SELL_FINAL',
                'Price': final_price,
                'Amount': amount_to_sell,
                'Commission': commission,
                'Cash_After_Trade': self.portfolio['cash'],
                'Assets_After_Trade': self.portfolio['assets']
            })

        self.equity_curve.loc[data.index[-1]] = self.portfolio['cash'] + self.portfolio['assets'] * data['Close Price'].iloc[-1]
        
        # 确保资金曲线索引是唯一的，并且排序
        self.equity_curve = self.equity_curve.loc[~self.equity_curve.index.duplicated(keep='last')].sort_index()
        return self.equity_curve, pd.DataFrame(self.trades)

    def analyze_performance(self, equity_curve, trades_df):
        # Add this block at the beginning of the method
        if trades_df.empty or 'Type' not in trades_df.columns:
            print("Warning: No trades recorded or 'Type' column not found in trades data. Returning default performance metrics.")
            # Return a default performance dictionary for no trades
            final_capital = equity_curve.iloc[-1] if not equity_curve.empty else self.initial_capital
            return {
                'Initial Capital': f"{self.initial_capital:,.2f}",
                'Final Capital': f"{final_capital:,.2f}",
                'Cumulative Return (%)': "0.00%",
                'Annualized Return (%)': "0.00%",
                'Max Drawdown (%)': "0.00%",
                'Sharpe Ratio': "0.00",
                'Total Trades': 0,
                'Win Rate (%)': "0.00%",
                'Profit/Loss Ratio': "0.00"
            }