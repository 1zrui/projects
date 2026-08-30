"""回测运行器 —— 编排 nautilus_trader 回测全流程

职责：
  - 从 DuckDB 加载数据
  - 创建 BacktestEngine（含模拟交易所）
  - 添加交易品种、数据、策略、执行算法
  - 运行回测
  - 生成标准报告
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money
from nautilus_trader.trading.strategy import Strategy

from backtest.adapter import (
    create_crypto_instrument,
    kline_df_to_bars,
    kline_to_bar_type,
)
from data.store import MarketStore
from nautilus_trader.model.currencies import USDT


class BacktestRunner:
    """回测运行器"""

    def __init__(
        self,
        store: MarketStore,
        config_path: str | Path = "config.yaml",
    ):
        self.store = store
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self._engine: BacktestEngine | None = None
        self._venue = Venue("BINANCE")

    # ── 运行单次回测 ──────────────────────────────────────

    def run(
        self,
        symbol: str,
        timeframe: str,
        strategy: Strategy,
        start: str | None = None,
        end: str | None = None,
        initial_capital: float | None = None,
        commission: float | None = None,
    ) -> dict[str, Any]:
        """运行一次回测

        Args:
            symbol: 交易对 e.g. 'BTC/USDT'
            timeframe: 粒度 e.g. '1h'
            strategy: nautilus Strategy 实例
            start: 开始时间 ISO 字符串
            end: 结束时间 ISO 字符串
            initial_capital: 初始资金（USDT）
            commission: 手续费率

        Returns:
            { reports: {...}, engine: BacktestEngine }
        """
        bt_config = self.config.get("backtest", {})
        start = start or bt_config.get("start")
        end = end or bt_config.get("end")
        capital = initial_capital or bt_config.get("initial_capital", 10000.0)
        comm = commission or bt_config.get("commission", 0.001)

        # 1. 从 DuckDB 加载数据
        print(f"[runner] 加载数据: {symbol} {timeframe} {start}~{end}")
        df = self.store.query_kline(symbol, timeframe, start=start, end=end)
        if df.empty:
            raise ValueError(f"无回测数据: {symbol} {timeframe} {start}~{end}")
        print(f"  → {len(df)} 根 K 线 ({df['timestamp'].min():%Y-%m-%d} ~ {df['timestamp'].max():%Y-%m-%d})")

        # 2. 创建交易品种
        instrument = create_crypto_instrument(symbol)
        bar_type = kline_to_bar_type(symbol, "BINANCE", timeframe)

        # 3. 转换数据
        bars = kline_df_to_bars(df, instrument, bar_type)
        print(f"  → 转换 nautilus bars: {len(bars)} 根")

        # 4. 创建引擎
        engine = BacktestEngine(
            config=BacktestEngineConfig(
                logging=LoggingConfig(log_level="ERROR"),
            ),
        )

        # 5. 添加模拟交易所
        engine.add_venue(
            venue=self._venue,
            oms_type=OmsType.NETTING,
            account_type=AccountType.CASH,
            base_currency=None,
            starting_balances=[Money(Decimal(str(capital)), USDT)],
        )

        # 6. 添加数据
        engine.add_instrument(instrument)
        engine.add_data(bars)

        # 7. 添加策略
        engine.add_strategy(strategy)

        # 8. 运行
        print(f"[runner] 开始回测 ...")
        engine.run()

        # 9. 生成报告
        reports = self._generate_reports(engine)
        reports["config"] = {
            "symbol": symbol,
            "timeframe": timeframe,
            "start": start,
            "end": end,
            "initial_capital": capital,
            "commission": comm,
            "bars": len(df),
        }

        self._engine = engine
        return {"reports": reports, "engine": engine}

    # ── 批量回测（多策略对比） ──────────────────────────────

    def run_batch(
        self,
        strategies: list[tuple[str, Strategy]],
        symbol: str,
        timeframe: str,
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        """对同一标的同时跑多个策略进行对比

        Args:
            strategies: [(name, Strategy 实例), ...]
        Returns:
            { strategy_name: { reports, metrics } }
        """
        results: dict[str, dict[str, Any]] = {}
        for name, strategy in strategies:
            print(f"\n{'='*60}")
            print(f"[batch] 策略: {name}")
            print(f"{'='*60}")
            result = self.run(symbol, timeframe, strategy, start, end)
            results[name] = result["reports"]
            # 释放引擎，避免全局状态冲突
            self._engine.dispose()
        return results

    # ── 报告生成 ──────────────────────────────────────────

    def _generate_reports(self, engine: BacktestEngine) -> dict[str, Any]:
        """生成回测报告"""
        reports: dict[str, Any] = {}

        try:
            reports["account"] = engine.trader.generate_account_report(self._venue)
        except Exception as e:
            reports["account"] = f"account report error: {e}"

        try:
            reports["positions"] = engine.trader.generate_positions_report()
        except Exception as e:
            reports["positions"] = f"positions report error: {e}"

        try:
            reports["fills"] = engine.trader.generate_order_fills_report()
        except Exception as e:
            reports["fills"] = f"fills report error: {e}"

        return reports

    def get_engine(self) -> BacktestEngine | None:
        return self._engine

    def dispose(self):
        if self._engine:
            self._engine.dispose()
            self._engine = None