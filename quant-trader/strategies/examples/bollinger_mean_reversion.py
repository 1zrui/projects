"""布林带均值回归策略

逻辑：
  - 价格跌破下轨 → 买入（超卖反弹）
  - 价格回到中轨 / 触及上轨 → 卖出（回归均值）
  - 适合震荡行情，不适合单边趋势

指标：
  - BOLL(20, 2)：20期均线 ± 2倍标准差
"""

from __future__ import annotations

from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators import BollingerBands
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.identifiers import InstrumentId

from strategies.base import QuantStrategy


class BollingerMeanReversionConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal = Decimal("5")      # 每笔名义金额 (USDT)
    bb_period: int = 20
    bb_std: float = 2.0


class BollingerMeanReversion(QuantStrategy):
    """布林带均值回归策略"""

    def __init__(self, config: BollingerMeanReversionConfig):
        super().__init__(config)
        self.bb = BollingerBands(
            period=config.bb_period,
            k=config.bb_std,
        )

    def on_start(self):
        self.register_indicator_for_bars(self.config.bar_type, self.bb)
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar):
        if not self.indicators_initialized():
            return
        if not self.bb.initialized:
            return

        lower = self.bb.lower
        upper = self.bb.upper
        mid = self.bb.middle
        close = float(bar.close.as_double())

        if self.is_flat():
            # 无持仓：价格跌破下轨 → 买入
            if close <= lower:
                self.buy_market()
        else:
            # 有持仓：价格回到中轨或触及上轨 → 卖出
            if close >= mid:
                self.flat()