"""RSI 超买超卖策略

逻辑：
  - RSI < 30 → 超卖，买入
  - RSI > 70 → 超买，卖出平仓
  - 适合震荡行情，小资金适用

指标：
  - RSI(14)
"""

from __future__ import annotations

from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators import RelativeStrengthIndex
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.identifiers import InstrumentId

from strategies.base import QuantStrategy


class RSIConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal = Decimal("5")      # 每笔名义金额 (USDT)
    rsi_period: int = 14
    oversold: float = 30.0    # 超卖阈值
    overbought: float = 70.0  # 超买阈值


class RSIStrategy(QuantStrategy):
    """RSI 超买超卖策略"""

    def __init__(self, config: RSIConfig):
        super().__init__(config)
        self.rsi = RelativeStrengthIndex(config.rsi_period)

    def on_start(self):
        self.register_indicator_for_bars(self.config.bar_type, self.rsi)
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar):
        if not self.indicators_initialized():
            return
        if not self.rsi.initialized:
            return

        rsi_value = self.rsi.value

        if self.is_flat():
            # RSI 超卖 → 买入
            if rsi_value <= self.config.oversold:
                self.buy_market()
        else:
            # RSI 超买 → 卖出平仓
            if rsi_value >= self.config.overbought:
                self.flat()