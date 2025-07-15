import backtrader as bt
import datetime

# 自定义 OBV 指标
class OBV(bt.Indicator):
    lines = ('obv',)
    plotinfo = dict(subplot=True)

    def __init__(self):
        obv_daily_change = bt.If(self.data.close > self.data.close(-1),
                                 self.data.volume,
                                 bt.If(self.data.close < self.data.close(-1),
                                       -self.data.volume,
                                       0))
        self.lines.obv = bt.If(bt.indicators.All(self.data.close(-1)),
                               obv_daily_change + self.lines.obv(-1), obv_daily_change)

class OBV_MACD_RSI_Strategy(bt.Strategy):
    params = dict(
        obv_period=10,
        rsi_period=10,
        macd1=8,
        macd2=17,
        macdsig=5,
        drawdown_limit=0.25,
        cooldown_period=5,
        rsi_overbought=70,
        rsi_oversold=30,
        atr_period=14,
        trailing_stop_multiplier=2.0,
        trailing_stop_active=True,
        buy_logic_type='MIXED',
        sell_logic_type='OR',
    )

    def __init__(self):
        self.order = None
        self.cooldown_counter = 0
        self.max_portfolio_value = self.broker.getvalue()
        self.highest_price_since_entry = -1

        self.obv = OBV(self.data)
        self.obv_ma = bt.ind.SMA(self.obv, period=self.p.obv_period)

        self.macd = bt.ind.MACD(self.data, period_me1=self.p.macd1,
                                 period_me2=self.p.macd2, period_signal=self.p.macdsig)
        self.macd_hist = self.macd.macd - self.macd.signal

        self.rsi = bt.ind.RSI(self.data, period=self.p.rsi_period)
        
        self.atr = bt.ind.ATR(self.data, period=self.p.atr_period)

    def log(self, txt, dt=None):
        dt = dt or self.data.datetime.date(0)
        print(f'{dt.isoformat()} {txt}')

    def next(self):
        if self.order:
            return

        current_value = self.broker.getvalue()
        self.max_portfolio_value = max(self.max_portfolio_value, current_value)
        drawdown = (self.max_portfolio_value - current_value) / self.max_portfolio_value

        if drawdown > self.p.drawdown_limit:
            self.log(f'❌ GLOBAL Drawdown {drawdown:.2%} triggered. Close positions.')
            if self.position:
                self.close()
            self.cooldown_counter = self.p.cooldown_period
            return

        if self.cooldown_counter > 0:
            self.cooldown_counter -= 1
            return

        pos = self.getposition().size

        obv_cross_up = self.obv[0] > self.obv_ma[0] and self.obv[-1] <= self.obv_ma[-1]
        obv_above_ma = self.obv[0] > self.obv_ma[0]

        macd_cross_up = self.macd_hist[0] > 0 and self.macd_hist[-1] <= 0
        rsi_not_overbought = self.rsi[0] < self.p.rsi_overbought
        rsi_oversold_bounce = self.rsi[0] > self.p.rsi_oversold and self.rsi[-1] <= self.p.rsi_oversold

        if not pos:
            buy_condition_met = False
            if self.data.close[0] > 0.00000001:
                if self.p.buy_logic_type == 'AND':
                    if obv_above_ma and macd_cross_up and rsi_not_overbought:
                        buy_condition_met = True
                elif self.p.buy_logic_type == 'OR':
                    if (obv_cross_up and macd_cross_up) or \
                       (obv_cross_up and rsi_oversold_bounce) or \
                       (macd_cross_up and rsi_oversold_bounce):
                        buy_condition_met = True
                elif self.p.buy_logic_type == 'MIXED':
                    if (obv_cross_up or macd_cross_up) and rsi_not_overbought:
                        buy_condition_met = True

            if buy_condition_met:
                size = int(self.broker.getcash() / self.data.close[0] * 0.95)
                if size > 0:
                    self.order = self.buy(size=size)
                    self.highest_price_since_entry = self.data.high[0]
                    self.log(f'✅ BUY at {self.data.close[0]:.6f}, Size: {size}')

        else:
            self.highest_price_since_entry = max(self.highest_price_since_entry, self.data.high[0])

            exit_obv_cross_down = self.obv[0] < self.obv_ma[0] and self.obv[-1] >= self.obv_ma[-1]
            exit_macd_cross_down = self.macd_hist[0] < 0 and self.macd_hist[-1] >= 0
            exit_rsi_overbought = self.rsi[0] > self.p.rsi_overbought

            sell_condition_met = False
            if self.p.sell_logic_type == 'OR':
                if exit_obv_cross_down or exit_macd_cross_down or exit_rsi_overbought:
                    sell_condition_met = True
            elif self.p.sell_logic_type == 'AND':
                if exit_obv_cross_down and exit_macd_cross_down and exit_rsi_overbought:
                    sell_condition_met = True

            if self.p.trailing_stop_active and self.highest_price_since_entry > 0:
                trailing_stop_price = self.highest_price_since_entry - (self.atr[0] * self.p.trailing_stop_multiplier)
                if self.data.close[0] < trailing_stop_price:
                    self.log(f'⚠️ Trailing Stop Loss triggered at {self.data.close[0]:.6f}')
                    self.order = self.sell(size=pos)
                    self.highest_price_since_entry = -1
                    return

            if sell_condition_met:
                self.order = self.sell(size=pos)
                self.highest_price_since_entry = -1
                self.log(f'🔻 SELL at {self.data.close[0]:.6f}, Size: {pos}')

    def stop(self):
        print(f'Final Portfolio Value: {self.broker.getvalue():.2f}')


if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(OBV_MACD_RSI_Strategy,
                        buy_logic_type='MIXED',
                        sell_logic_type='OR',
                        drawdown_limit=0.3,
                        cooldown_period=5,
                        rsi_overbought=70,
                        trailing_stop_active=True,
                        trailing_stop_multiplier=2.0)

    data = bt.feeds.GenericCSVData(
        dataname=r'stock_quant\data\day\SOLUSDT_1d.csv',
        dtformat='%Y-%m-%d',
        datetime=0, open=1, high=2, low=3, close=4, volume=5, openinterest=-1,
        fromdate=datetime.datetime(2021, 1, 1),
        todate=datetime.datetime(2024, 12, 31)
    )
    cerebro.adddata(data)
    cerebro.broker.setcash(10000)
    cerebro.broker.setcommission(commission=0.001)

    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    results = cerebro.run()
    strat = results[0]

    print('\n--- 分析报告 ---')
    print(f"Sharpe Ratio: {strat.analyzers.sharpe.get_analysis().get('sharperatio', 'N/A')}")
    dd = strat.analyzers.drawdown.get_analysis()
    print(f"Max Drawdown: {dd['max']['drawdown']:.2f}%")
    print(f"Max Drawdown Duration: {dd['max']['len']} bars")
    print("\nAnnual Return:")
    annual_returns = strat.analyzers.annual.get_analysis()
    for year, ret in annual_returns.items():
        print(f"{year}: {ret*100:.2f}%")

    trades_analysis = strat.analyzers.trades.get_analysis()
    print("\n✅ Raw Trade Analysis:", trades_analysis)

    if 'total' in trades_analysis and 'closed' in trades_analysis.total:
        total_closed = trades_analysis.total.closed
        total_won = trades_analysis.won.total
        total_lost = trades_analysis.lost.total
        print(f"\nTotal Trades: {total_closed}")
        print(f"Winning Trades: {total_won}")
        print(f"Losing Trades: {total_lost}")
        win_rate = (total_won / total_closed * 100) if total_closed > 0 else 0
        print(f"Win Rate: {win_rate:.2f}%")
    else:
        print("\n⚠️ No closed trades found in the analysis.")

    cerebro.plot()
