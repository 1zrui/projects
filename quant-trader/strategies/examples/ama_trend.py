"""适应性均线趋势 —— 自动适应市场波动

AMA（自适应移动平均）在市场震荡时变平滑（少假信号），
趋势明显时变灵敏（快跟上），自动调节。

逻辑：
  - AMA(10,2,30) 上升且空仓 → 买入
  - AMA 下降且有持仓 → 卖出
"""

from __future__ import annotations

from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators import AdaptiveMovingAverage
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.identifiers import InstrumentId

from strategies.base import QuantStrategy


class AMATrendConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal = Decimal("3")
    period: int = 10
    fast_scale: int = 2
    slow_scale: int = 30


class AMATrend(QuantStrategy):
    """适应性均线趋势策略"""

    def __init__(self, config: AMATrendConfig):
        super().__init__(config)
        self.ama = AdaptiveMovingAverage(
            config.period, config.fast_scale, config.slow_scale,
        )

    def on_start(self):
        self.register_indicator_for_bars(self.config.bar_type, self.ama)
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar):
        if not self.indicators_initialized():
            return
        if not self.ama.initialized:
            return

        current = self.ama.value
        if not hasattr(self, "_prev_ama"):
            self._prev_ama = current
            return
        prev = self._prev_ama
        self._prev_ama = current

        rising = current > prev
        falling = current < prev

        if rising and self.is_flat():
            self.buy_market()
        elif falling and not self.is_flat():
            self.flat()