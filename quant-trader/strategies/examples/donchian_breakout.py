"""突破策略 —— Donchian 通道 + 止损/止盈"""

from __future__ import annotations

from collections import deque
from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.identifiers import InstrumentId

from strategies.base import QuantStrategy


class DonchianBreakoutConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal = Decimal("5")
    entry_period: int = 20       # 突破周期
    exit_period: int = 10        # 退出周期（反向突破）
    stop_loss_pct: float = 0.03  # 3% 止损
    take_profit_pct: float = 0.06  # 6% 止盈


class DonchianBreakout(QuantStrategy):
    """Donchian 通道突破：突破 N 日高点做多，跌破 M 日低点离场"""

    def __init__(self, config: DonchianBreakoutConfig):
        super().__init__(config)
        self._highs: deque[float] = deque(maxlen=config.entry_period)
        self._lows: deque[float] = deque(maxlen=config.entry_period)
        self._exit_lows: deque[float] = deque(maxlen=config.exit_period)
        self._entry_price: float | None = None
        self._bars_seen = 0

    def on_start(self):
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar):
        close = float(bar.close)
        high = float(bar.high)
        low = float(bar.low)

        self._bars_seen += 1

        # 预热
        if len(self._highs) < self.config.entry_period:
            self._highs.append(high)
            self._lows.append(low)
            self._exit_lows.append(low)
            return

        donchian_high = max(self._highs)
        donchian_low = min(self._lows)
        exit_low = min(self._exit_lows) if len(self._exit_lows) >= self.config.exit_period else donchian_low

        # 更新
        self._highs.append(high)
        self._lows.append(low)
        self._exit_lows.append(low)

        if self._bars_seen < self.config.entry_period + 5:
            return

        if self.is_flat():
            if close > donchian_high:
                self.buy_market()
                self._entry_price = close
        else:
            # 止损止盈
            if self._entry_price is not None:
                ret = (close - self._entry_price) / self._entry_price
                if ret <= -self.config.stop_loss_pct:
                    self.flat()
                    self._entry_price = None
                    return
                if ret >= self.config.take_profit_pct:
                    self.flat()
                    self._entry_price = None
                    return
            # 通道退出
            if close < exit_low:
                self.flat()
                self._entry_price = None

    def on_order_filled(self, event):
        # 记录入场价
        pass
