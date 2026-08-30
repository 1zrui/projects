"""EMA 交叉策略 —— 经典示例策略（现货多头版）

逻辑（现货 CASH 账户，只做多）：
  - 快EMA（10）上穿慢EMA（20）→ 买入
  - 快EMA（10）下穿慢EMA（20）→ 卖出平仓
  - 已持仓时不重复开仓
"""

from __future__ import annotations

from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.identifiers import InstrumentId

from strategies.base import QuantStrategy


class EMACrossConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal = Decimal("10")      # 每笔名义金额 (USDT)
    fast_ema_period: int = 10
    slow_ema_period: int = 20


class EMACross(QuantStrategy):
    """EMA 交叉策略（现货多头）"""

    def __init__(self, config: EMACrossConfig):
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
            # 多头信号且无持仓 → 买入
            self.buy_market()
        elif fast < slow and not self.is_flat():
            # 空头信号且有持仓 → 平仓
            self.flat()