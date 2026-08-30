"""Hull 移动平均线趋势 —— 更平滑，减少滞后

Hull MA 比普通 EMA 更平滑、滞后更小，能更快捕捉趋势转折。

逻辑：
  - HullMA(20) 上升（当前 > 前一根）且空仓 → 买入
  - HullMA(20) 下降（当前 < 前一根）且有持仓 → 卖出
"""

from __future__ import annotations

from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators import HullMovingAverage
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.identifiers import InstrumentId

from strategies.base import QuantStrategy


class HullTrendConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal = Decimal("3")
    period: int = 20


class HullTrend(QuantStrategy):
    """Hull 移动平均趋势策略"""

    def __init__(self, config: HullTrendConfig):
        super().__init__(config)
        self.hull = HullMovingAverage(config.period)

    def on_start(self):
        self.register_indicator_for_bars(self.config.bar_type, self.hull)
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar):
        if not self.indicators_initialized():
            return
        if not self.hull.initialized:
            return

        current = self.hull.value
        # 获取前一根 Hull 值（用 python 侧维护历史）
        if not hasattr(self, "_prev_hull"):
            self._prev_hull = current
            return
        prev = self._prev_hull
        self._prev_hull = current

        rising = current > prev
        falling = current < prev

        if rising and self.is_flat():
            self.buy_market()
        elif falling and not self.is_flat():
            self.flat()