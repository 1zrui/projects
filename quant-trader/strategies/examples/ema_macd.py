"""EMA + MACD 组合策略（带止损止盈）

借鉴 GitHub 开源策略思路，结合三种技术：
  - EMA(20,50) 判断趋势方向
  - MACD(12,26,9) 金叉/死叉确认信号
  - 止损 1% / 止盈 2% 控制单笔盈亏

比单 EMA 更稳健，MACD 过滤假信号，止损止盈控风险。
"""

from __future__ import annotations

from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators import ExponentialMovingAverage, MovingAverageConvergenceDivergence
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide, PositionSide
from nautilus_trader.model.identifiers import InstrumentId

from strategies.base import QuantStrategy


class EMAMACDConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal = Decimal("3")       # 每笔名义金额 (USDT)
    fast_ema: int = 20
    slow_ema: int = 50
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    stop_loss_pct: float = 0.01              # 止损 1%
    take_profit_pct: float = 0.02            # 止盈 2%


class EMAMACD(QuantStrategy):
    """EMA 趋势 + MACD 确认 + 止损止盈"""

    def __init__(self, config: EMAMACDConfig):
        super().__init__(config)
        self.fast_ema = ExponentialMovingAverage(config.fast_ema)
        self.slow_ema = ExponentialMovingAverage(config.slow_ema)
        self.macd = MovingAverageConvergenceDivergence(
            config.macd_fast, config.macd_slow,
        )

    def on_start(self):
        self.register_indicator_for_bars(self.config.bar_type, self.fast_ema)
        self.register_indicator_for_bars(self.config.bar_type, self.slow_ema)
        self.register_indicator_for_bars(self.config.bar_type, self.macd)
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar):
        if not self.indicators_initialized():
            return

        price = float(bar.close.as_double())

        # 已有持仓 → 检查止损止盈
        if not self.is_flat():
            pos = self._get_position()
            if pos is not None:
                entry = float(pos.avg_px_open)
                if pos.side == PositionSide.LONG:
                    pnl_pct = (price - entry) / entry
                    if pnl_pct <= -self.config.stop_loss_pct:
                        self.flat()
                        return
                    elif pnl_pct >= self.config.take_profit_pct:
                        self.flat()
                        return
            # 没触发止损止盈，不操作
            return

        # 空仓 → 检查入场信号
        # 条件：EMA20 > EMA50（趋势向上）+ MACD 金叉
        ema_fast = self.fast_ema.value
        ema_slow = self.slow_ema.value
        macd_value = self.macd.value

        if ema_fast is None or ema_slow is None or macd_value is None:
            return

        trend_up = ema_fast >= ema_slow
        momentum_up = macd_value > 0  # MACD > 0 = 动量向上

        if trend_up and momentum_up:
            self.buy_market()

    def _get_position(self):
        """获取当前持仓对象"""
        for pos in self.cache.positions():
            if pos.instrument_id == self.config.instrument_id and pos.is_open:
                return pos
        return None