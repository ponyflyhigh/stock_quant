import backtrader as bt
import datetime

class CombinedStrategy(bt.Strategy):
    params = dict(
        ma_short=5,
        ma_long=20,
        macd_fast=12,
        macd_slow=26,
        macd_signal=9,
        rsi_period=14,
        rsi_overbought=70,
        size_pct=0.95,
    )

    def __init__(self):
        # 均线
        self.ma_short = bt.ind.SMA(self.data.close, period=self.p.ma_short)
        self.ma_long = bt.ind.SMA(self.data.close, period=self.p.ma_long)
        
        # MACD
        self.macd = bt.ind.MACD(self.data.close,
                                period_me1=self.p.macd_fast,
                                period_me2=self.p.macd_slow,
                                period_signal=self.p.macd_signal)
        
        # RSI
        self.rsi = bt.ind.RSI(self.data.close, period=self.p.rsi_period)

        self.order = None

    def log(self, txt):
        dt = self.datas[0].datetime.date(0)
        print(f'{dt} - {txt}')

    def next(self):
        if self.order:
            return  # 有订单未完成

        pos = self.getposition().size

        # 入场逻辑：MA金叉 + MACD金叉 + RSI未超买
        buy_signal = (
            self.ma_short[0] > self.ma_long[0] and
            self.ma_short[-1] <= self.ma_long[-1] and
            self.macd.macd[0] > self.macd.signal[0] and
            self.macd.macd[-1] <= self.macd.signal[-1] and
            self.rsi[0] < self.p.rsi_overbought
        )

        # 出场逻辑：MA死叉 或 MACD死叉 或 RSI过热
        sell_signal = (
            self.ma_short[0] < self.ma_long[0] or
            (self.macd.macd[0] < self.macd.signal[0] and self.macd.macd[-1] >= self.macd.signal[-1]) or
            self.rsi[0] > self.p.rsi_overbought
        )

        # 买入逻辑
        if not pos and buy_signal:
            size = int(self.broker.getcash() / self.data.close[0] * self.p.size_pct)
            if size > 0:
                self.log(f'✅ BUY @ {self.data.close[0]:.2f}')
                self.order = self.buy(size=size)

        # 卖出逻辑
        elif pos and sell_signal:
            self.log(f'🔻 SELL @ {self.data.close[0]:.2f}')
            self.order = self.sell(size=pos)

    def stop(self):
        self.log(f'Final Portfolio Value: {self.broker.getvalue():.2f}')

# -----------------------------
# 回测引擎设置
# -----------------------------
if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(CombinedStrategy)

    data = bt.feeds.GenericCSVData(
        dataname=r'stock_quant\data\day\ETHUSDT_1d.csv',  # 改为你自己的 CSV 文件路径
        dtformat='%Y-%m-%d',
        datetime=0,
        open=1,
        high=2,
        low=3,
        close=4,
        volume=5,
        openinterest=-1,
        fromdate=datetime.datetime(2021, 1, 1),
        todate=datetime.datetime(2024, 12, 31)
    )

    cerebro.adddata(data)
    cerebro.broker.setcash(10000)
    cerebro.broker.setcommission(commission=0.001)

    # 分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    results = cerebro.run()
    strat = results[0]

    print('\n--- 回测分析 ---')
    print(f"Sharpe Ratio: {strat.analyzers.sharpe.get_analysis().get('sharperatio', 'N/A')}")
    dd = strat.analyzers.drawdown.get_analysis()
    print(f"Max Drawdown: {dd['max']['drawdown']:.2f}%")

    trades = strat.analyzers.trades.get_analysis()

    cerebro.plot()
