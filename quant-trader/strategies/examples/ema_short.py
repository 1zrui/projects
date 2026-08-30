"""EMA 趋势跟踪（短线版）

对比 EMA趋势(50,200)：
  - 均线更短（20/50），信号更频繁
  - 不带止损（先看基础表现）

逻辑：
  - EMA(20) >= EMA(50) 且空仓 → 买入
  - EMA(20) < EMA(50) 且有持仓 → 卖出
"""

from __future__ import annotations

from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.identifiers import InstrumentId

from strategies.base import QuantStrategy


class EMAShortConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal = Decimal("3")       # 每笔名义金额 (USDT)
    fast_ema_period: int = 20
    slow_ema_period: int = 50


class EMAShort(QuantStrategy):
    """EMA 趋势跟踪短线版"""

    def __init__(self, config: EMAShortConfig):
        super().__init__(config)
        self.fast_ema = ExponentialMovingAverage(config.fast_ema_period)
        self.slow_ema = ExponentialMovingAverage(config.slow_ema_period)

    def on_start(self):
        self.register_indicator_for_bars(self.config.bar_type, self.fast_ema)
        self.register_indicator_for_bars(self.config.bar_type, self.slow_ema)
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar):
        if not self.indicators_initialized():
            return

        fast = self.fast_ema.value
        slow = self.slow_ema.value

        if fast >= slow and self.is_flat():
            self.buy_market()
        elif fast < slow and not self.is_flat():
            self.flat()