"""多指标超卖确认策略（大哥提供的方案）

4 个指标同时确认超卖 → 买入（底部信号）
所有指标脱离超卖 → 卖出（反弹到位）

指标 & 超卖阈值：
  - RSI(14)        < 21
  - Stochastic(14) < 8
  - CCI(20)        < -105
  - Williams %R(14) < -92   （由 Stochastic %K - 100 推导）

买入条件：至少 3 个指标超卖
卖出条件：0 个指标超卖（全部脱离）
"""

from __future__ import annotations

from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators import (
    RelativeStrengthIndex,
    Stochastics,
    CommodityChannelIndex,
)
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.identifiers import InstrumentId

from strategies.base import QuantStrategy


class MultiOversoldConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal = Decimal("5")       # 每笔名义金额 (USDT)
    rsi_period: int = 14
    rsi_oversold: float = 21.0
    stoch_period: int = 14
    stoch_oversold: float = 8.0
    cci_period: int = 20
    cci_oversold: float = -105.0
    wr_period: int = 14
    wr_oversold: float = -92.0
    min_oversold: int = 3                     # 至少几个指标超卖才买


class MultiOversold(QuantStrategy):
    """多指标超卖确认策略"""

    def __init__(self, config: MultiOversoldConfig):
        super().__init__(config)
        self.rsi = RelativeStrengthIndex(config.rsi_period)
        self.stoch = Stochastics(config.stoch_period, config.stoch_period)
        self.cci = CommodityChannelIndex(config.cci_period)

    def on_start(self):
        self.register_indicator_for_bars(self.config.bar_type, self.rsi)
        self.register_indicator_for_bars(self.config.bar_type, self.stoch)
        self.register_indicator_for_bars(self.config.bar_type, self.cci)
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar):
        if not self.indicators_initialized():
            return
        if not (self.rsi.initialized and self.stoch.initialized and self.cci.initialized):
            return

        # Williams %R = Stochastic %K - 100（同一 14 周期公式推导）
        stoch_k = self.stoch.value_k
        williams_r = stoch_k - 100.0

        rsi_val = float(self.rsi.value)
        stoch_val = float(self.stoch.value_k)
        cci_val = float(self.cci.value)

        # 统计超卖指标个数
        n_oversold = 0
        if rsi_val < self.config.rsi_oversold:
            n_oversold += 1
        if stoch_val < self.config.stoch_oversold:
            n_oversold += 1
        if cci_val < self.config.cci_oversold:
            n_oversold += 1
        if williams_r < self.config.wr_oversold:
            n_oversold += 1

        if self.is_flat():
            # 至少 3 个指标超卖 → 买入
            if n_oversold >= self.config.min_oversold:
                self.buy_market()
        else:
            # 0 个指标超卖 → 卖出（反弹到位）
            if n_oversold == 0:
                self.flat()