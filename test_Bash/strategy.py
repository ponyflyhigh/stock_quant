import pandas as pd
import numpy as np

class Strategy:
    def __init__(self, name, params):
        self.name = name
        self.params = params

    def generate_signals(self, data):
        """
        根据策略逻辑生成买入/卖出信号。
        data: 包含指标的 DataFrame
        返回: 包含 'Signal' 列的 DataFrame (1: 买入, -1: 卖出, 0: 持有)
        """
        data['Signal'] = 0

        if self.name == "macd":
            # MACD 金叉买入 (MACD 上穿 Signal Line)
            data.loc[data['MACD'] > data['MACD_Signal'], 'Signal'] = 1
            # MACD 死叉卖出 (MACD 下穿 Signal Line)
            data.loc[data['MACD'] < data['MACD_Signal'], 'Signal'] = -1
            
            # 仅在信号发生变化时产生交易信号
            # 例如：从持有到买入，从持有到卖出
            # data['Position'] = data['Signal'].diff()
            # 1: 买入，-1: 卖出, 0: 不动
            # 为了简化，这里直接用 Signal 作为 Position，回测器会处理实际交易点
            
        elif self.name == "moving_average_crossover":
            # 示例：短期均线穿过长期均线
            # data['Short_MA'] = data['Close Price'].rolling(window=self.params['short_period']).mean()
            # data['Long_MA'] = data['Close Price'].rolling(window=self.params['long_period']).mean()
            # data.loc[data['Short_MA'] > data['Long_MA'], 'Signal'] = 1
            # data.loc[data['Short_MA'] < data['Long_MA'], 'Signal'] = -1
            pass # 占位符，如果启用需要计算 MA 指标

        else:
            raise ValueError(f"Unknown strategy name: {self.name}")

        return data