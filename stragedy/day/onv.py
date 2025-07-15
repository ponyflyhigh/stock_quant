import backtrader as bt
import pandas as pd

# ----------------------
# 自定义 OBV 指标
# ----------------------
class OBV(bt.Indicator):
    lines = ('obv',)
    plotinfo = dict(subplot=True)

    def __init__(self):
        self.addminperiod(1)

    def next(self):
        if len(self) == 1:
            self.lines.obv[0] = self.data.volume[0]
        else:
            if self.data.close[0] > self.data.close[-1]:
                self.lines.obv[0] = self.lines.obv[-1] + self.data.volume[0]
            elif self.data.close[0] < self.data.close[-1]:
                self.lines.obv[0] = self.lines.obv[-1] - self.data.volume[0]
            else:
                self.lines.obv[0] = self.lines.obv[-1]


# ----------------------
# 策略定义
# ----------------------
class OBVStrategy(bt.Strategy):
    params = dict(
        obv_ma_period=20,
        printlog=True,
        size_percentage=0.95,
    )

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        if self.p.printlog:
            print(f'{dt.isoformat()}, {txt}')

    def __init__(self):
        self.order = None
        self.dataclose = self.datas[0].close

        self.obv = OBV(self.datas[0])
        self.obv_ma = bt.indicators.SMA(self.obv, period=self.p.obv_ma_period)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status == order.Completed:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}')
            elif order.issell():
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

        if not pos:
            # OBV 上穿 OBV 均线，买入
            if self.obv[0] > self.obv_ma[0] and self.obv[-1] <= self.obv_ma[-1]:
                cash = self.broker.getcash() * self.p.size_percentage
                size = int(cash / self.dataclose[0])
                if size > 0:
                    self.log(f'BUY CREATE, Price: {self.dataclose[0]:.2f}, Size: {size}')
                    self.order = self.buy(size=size)
        else:
            # OBV 下穿 OBV 均线，卖出
            if self.obv[0] < self.obv_ma[0] and self.obv[-1] >= self.obv_ma[-1]:
                self.log(f'SELL CREATE, Price: {self.dataclose[0]:.2f}, Size: {pos}')
                self.order = self.sell(size=pos)

    def stop(self):
        self.log(f'Final Portfolio Value: {self.broker.getvalue():.2f}')


# ----------------------
# 回测主程序
# ----------------------
if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(OBVStrategy)

    # 加载 CSV 数据
    data = bt.feeds.GenericCSVData(
        dataname=r'stock_quant\data\day\DOGEUSDT_1d.csv',  # ✅ 替换为你自己的绝对路径
        dtformat='%Y-%m-%d',
        datetime=0,
        open=1,
        high=2,
        low=3,
        close=4,
        volume=5,
        openinterest=-1,
        reverse=False
    )
    cerebro.adddata(data)

    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.00075)

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual')

    print(f'Starting Portfolio Value: {cerebro.broker.getvalue():.2f}')
    results = cerebro.run()
    strat = results[0]
    print(f'Final Portfolio Value: {cerebro.broker.getvalue():.2f}')

    # 分析报告
    print('\n--- 分析报告 ---')
    print(f"Sharpe Ratio: {strat.analyzers.sharpe.get_analysis().get('sharperatio', 'N/A')}")
    dd = strat.analyzers.drawdown.get_analysis()
    print(f"Max Drawdown: {dd['max']['drawdown']:.2f}%")
    print(f"Max Drawdown Duration: {dd['max']['len']} bars")

    print("\nAnnual Return:")
    for year, ret in strat.analyzers.annual.get_analysis().items():
        print(f"{year}: {ret*100:.2f}%")

    # 绘图
    cerebro.plot(style='candlestick')
