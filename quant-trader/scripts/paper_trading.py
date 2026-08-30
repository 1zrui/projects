#!/usr/bin/env python
"""模拟交易 —— 每小时跑一次，记录策略信号，不真下单

流程：
  1. 增量更新数据（拉最新 1h K 线）
  2. 用最近 500 根 K 线跑回测（快速）
  3. 看策略最后状态（持仓/空仓）
  4. 记录信号到日志
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pandas as pd

from data.store import MarketStore
from data.pipeline import DataPipeline
from data.collector import BinanceCollector
from data.symbols import load_config
from backtest.runner import BacktestRunner
from backtest.adapter import create_crypto_instrument, kline_to_bar_type
from strategies.examples.ema_trend import EMATrend, EMATrendConfig

LOG_FILE = Path("paper_trading.log")
LOOKBACK = 500  # 用最近 500 根 K 线跑回测


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    print("=" * 50)
    print("模拟交易 · 信号检查")
    print("=" * 50)

    cfg = load_config()
    symbol = cfg.get("symbols", ["BTC/USDT"])[0]
    timeframe = cfg.get("timeframes", ["1h"])[0]
    capital = cfg.get("backtest", {}).get("initial_capital", 100.0)

    # 1. 增量更新数据
    print("\n[1] 增量更新数据 ...")
    store = MarketStore("data/market_data.duckdb")
    collector = BinanceCollector(
        market_type="spot",
        proxy=cfg.get("exchange", {}).get("proxy"),
    )
    pipe = DataPipeline(store, collector)
    n = pipe.incremental_update(symbol, timeframe)
    print(f"    新增 {n} 根 K 线")

    # 2. 查最新数据范围
    latest = store.get_latest_timestamp(symbol, timeframe)
    if latest is None:
        log("❌ 无数据，跳过")
        store.close()
        return
    print(f"\n[2] 最新数据: {latest}")

    # 3. 用最近 LOOKBACK 根 K 线跑回测
    print(f"\n[3] 跑回测（最近 {LOOKBACK} 根）...")
    instrument = create_crypto_instrument(symbol)
    bar_type = kline_to_bar_type(symbol, "BINANCE", timeframe)

    strategy = EMATrend(
        EMATrendConfig(
            instrument_id=instrument.id,
            bar_type=bar_type,
            trade_size=Decimal("3"),
        ),
    )

    # 计算开始时间
    start = latest - pd.Timedelta(hours=LOOKBACK)

    runner = BacktestRunner(store)
    result = runner.run(
        symbol=symbol,
        timeframe=timeframe,
        strategy=strategy,
        start=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

    reports = result["reports"]
    account = reports.get("account")
    positions = reports.get("positions")

    # 4. 判断当前状态
    if isinstance(account, pd.DataFrame) and "currency" in account.columns:
        usdt = account[account["currency"] == "USDT"].copy()
        usdt["total"] = usdt["total"].astype(float)
        balance = usdt["total"].iloc[-1] if not usdt.empty else capital
    else:
        balance = capital

    # 检查是否有持仓
    has_position = False
    if isinstance(positions, pd.DataFrame) and not positions.empty:
        # 看最后一条持仓是否还是 open 状态
        has_position = True

    pnl = balance - capital

    # 5. 记录信号
    signal = "📈 持仓中" if has_position else "📉 空仓"
    status = (
        f"余额: ${balance:.2f} | 本金: ${capital:.2f} | "
        f"盈亏: ${pnl:+.2f} ({pnl/capital*100:+.2f}%) | "
        f"状态: {signal}"
    )
    log(status)

    # 6. 交易摘要
    if isinstance(positions, pd.DataFrame) and not positions.empty:
        total_trades = len(positions)
        log(f"模拟交易次数: {total_trades}")

    runner.dispose()
    store.close()

    print(f"\n{'='*50}")
    print(f"✅ 模拟交易检查完成")
    print(f"   日志: {LOG_FILE.resolve()}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()