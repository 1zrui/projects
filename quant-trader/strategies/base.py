"""策略基类 —— 所有量化策略的模板

使用方式：
  class MyStrategy(QuantStrategy):
      ...
"""

from __future__ import annotations

from decimal import Decimal
from typing import ClassVar

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import OrderSide, PriceType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy


class QuantStrategyConfig(StrategyConfig, frozen=True):
    """策略配置基类"""
    instrument_id: InstrumentId
    trade_size: Decimal = Decimal("1000")     # 每笔交易名义金额（USDT）
    stop_loss_pct: Decimal = Decimal("0.02")   # 止损比例 2%
    take_profit_pct: Decimal = Decimal("0.05") # 止盈比例 5%


class QuantStrategy(Strategy):
    """量化策略基类，封装常用交易操作"""

    def __init__(self, config: QuantStrategyConfig):
        super().__init__(config)

    # ── 下单辅助 ──────────────────────────────────────────

    def buy_market(self, notional: Decimal | None = None):
        """市价买入（按名义金额 USDT，自动换算数量）"""
        instrument = self.cache.instrument(self.config.instrument_id)
        price = self.cache.price(self.config.instrument_id, PriceType.LAST)
        if price is None:
            self.log.warning("无价格数据，跳过买入")
            return
        trade_val = notional or self.config.trade_size
        qty = instrument.make_qty(trade_val / price)
        order = self.order_factory.market(
            self.config.instrument_id, OrderSide.BUY, qty,
        )
        self.submit_order(order)

    def sell_market(self, notional: Decimal | None = None):
        """市价卖出（按名义金额 USDT，自动换算数量）"""
        instrument = self.cache.instrument(self.config.instrument_id)
        price = self.cache.price(self.config.instrument_id, PriceType.LAST)
        if price is None:
            self.log.warning("无价格数据，跳过卖出")
            return
        trade_val = notional or self.config.trade_size
        qty = instrument.make_qty(trade_val / price)
        order = self.order_factory.market(
            self.config.instrument_id, OrderSide.SELL, qty,
        )
        self.submit_order(order)

    def flat(self):
        """平掉当前持仓"""
        self.close_all_positions(self.config.instrument_id)

    # ── 仓位查询 ──────────────────────────────────────────

    def is_flat(self) -> bool:
        return self.portfolio.is_flat(self.config.instrument_id)

    def is_net_long(self) -> bool:
        return self.portfolio.is_net_long(self.config.instrument_id)

    def is_net_short(self) -> bool:
        return self.portfolio.is_net_short(self.config.instrument_id)

    # ── 子类需要实现 ──────────────────────────────────────

    def on_bar(self, bar: Bar):
        """每根新 K 线触发——子类实现策略逻辑"""
        raise NotImplementedError

    def on_start(self):
        """引擎启动时触发——子类初始化指标"""
        pass

    def on_stop(self):
        """引擎停止时触发——子类清理"""
        self.close_all_positions(self.config.instrument_id)