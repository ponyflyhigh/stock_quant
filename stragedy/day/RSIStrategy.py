import backtrader as bt
import pandas as pd

class RSIStrategy(bt.Strategy):
    params = (
        ('rsi_period', 14),
        ('rsi_lower', 30),
        ('rsi_upper', 70),
        ('size_percentage', 0.95),
        ('printlog', True)
    )

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        if self.p.printlog:
            print(f'{dt.isoformat()}, {txt}')

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None
        self.rsi = bt.indicators.RSI_SMA(self.dataclose, period=self.p.rsi_period)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status == order.Completed:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}')
            else:
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}')
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if trade.isclosed:
            self.log(f'PROFIT, Gross: {trade.pnl:.2f}, Net: {trade.pnlcomm:.2f}')

    def next(self):
        if self.order:
            return

        pos = self.getposition().size

        # 仅使用 RSI 指标判断
        if not pos:
            if self.rsi[0] < self.p.rsi_lower:
                cash = self.broker.getcash() * self.p.size_percentage
                size = int(cash / self.dataclose[0])
                if size > 0:
                    self.log(f'BUY CREATE, Price: {self.dataclose[0]:.2f}, Size: {size}')
                    self.order = self.buy(size=size)
        else:
            if self.rsi[0] > self.p.rsi_upper:
                self.log(f'SELL CREATE, Price: {self.dataclose[0]:.2f}, Size: {pos}')
                self.order = self.sell(size=pos)

    def stop(self):
        self.log(f'Final Portfolio Value: {self.broker.getvalue():.2f}')


# --- 回测主程序 ---
if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(RSIStrategy)

    # 加载数据
    data = bt.feeds.GenericCSVData(
        dataname='stock_quant/data/ETHUSDT_1d.csv',
        dtformat='%Y-%m-%d',
        datetime=0,
        open=1,
        high=2,
        low=3,
        close=4,
        volume=5,
        openinterest=-1,
        nullvalue=0.0,
        reverse=False,
        headers=True
    )

    cerebro.adddata(data)

    # 初始资金和手续费设置
    cerebro.broker.setcash(10000)
    cerebro.broker.setcommission(commission=0.001)

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual')

    print(f"Starting Portfolio Value: {cerebro.broker.getvalue():.2f}")
    results = cerebro.run()
    strat = results[0]
    print(f"Final Portfolio Value: {cerebro.broker.getvalue():.2f}")

    # --- 分析报告 ---
    print('\n--- 分析报告 ---')
    print(f"Sharpe Ratio: {strat.analyzers.sharpe.get_analysis().get('sharperatio', 'N/A')}")
    dd = strat.analyzers.drawdown.get_analysis()
    print(f"Max Drawdown: {dd['max']['drawdown']:.2f}%")
    print(f"Max Drawdown Duration: {dd['max']['len']} bars")

    print("\nAnnual Return:")
    for year, ret in strat.analyzers.annual.get_analysis().items():
        print(f"{year}: {ret * 100:.2f}%")

    # --- 绘图 ---
    cerebro.plot(style='candlestick')
