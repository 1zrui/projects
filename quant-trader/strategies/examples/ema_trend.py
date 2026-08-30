"""EMA 趋势跟踪策略 —— 稳中求进版

核心思路：
  - 长周期均线判断趋势方向，减少假信号
  - 小仓位，降低波动风险
  - 持仓时间长，减少手续费损耗

逻辑：
  - EMA(50) 上穿 EMA(200) → 趋势转多，买入
  - EMA(50) 下穿 EMA(200) → 趋势转空，卖出平仓
  - 只做多，顺势而为
"""

from __future__ import annotations

from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.identifiers import InstrumentId

from strategies.base import QuantStrategy


class EMATrendConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal = Decimal("3")       # 每笔名义金额 (USDT)
    fast_ema_period: int = 50
    slow_ema_period: int = 200


class EMATrend(QuantStrategy):
    """EMA 趋势跟踪策略（稳中求进版）"""

    def __init__(self, config: EMATrendConfig):
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
            # 多头趋势，无持仓 → 买入
            self.buy_market()
        elif fast < slow and not self.is_flat():
            # 空头趋势，有持仓 → 平仓
            self.flat()