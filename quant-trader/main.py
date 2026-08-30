#!/usr/bin/env python
"""quant-trader —— 量化回测平台入口

命令:
  python main.py sync          # 全量拉取数据
  python main.py update        # 增量更新数据
  python main.py run           # 运行回测（默认策略）
  python main.py status        # 查看数据状态
  python main.py quality       # 查看数据质量报告
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from data.collector import BinanceCollector
from data.pipeline import DataPipeline
from data.symbols import get_symbols, get_timeframes
from data.store import MarketStore


def load_config():
    with open("config.yaml") as f:
        return yaml.safe_load(f)


def get_store() -> MarketStore:
    cfg = load_config()
    db_path = Path(cfg["store"]["path"])
    return MarketStore(db_path)


def get_collector() -> BinanceCollector:
    cfg = load_config()
    exchange_cfg = cfg.get("exchange", {})
    return BinanceCollector(
        market_type=exchange_cfg.get("type", "spot"),
        proxy=exchange_cfg.get("proxy"),
    )


def get_pipeline() -> DataPipeline:
    return DataPipeline(get_store(), get_collector())


def cmd_sync():
    """全量拉取数据"""
    cfg = load_config()
    pipe = get_pipeline()
    symbols = cfg.get("symbols", ["BTC/USDT"])
    timeframes = cfg.get("timeframes", ["1h", "4h", "1d"])
    start = cfg.get("backtest", {}).get("start", "2024-01-01")
    end = cfg.get("backtest", {}).get("end")

    print(f"📡 全量数据同步")
    print(f"   交易对: {symbols}")
    print(f"   粒度:   {timeframes}")
    print(f"   区间:   {start} ~ {end or '现在'}")
    print()

    results = pipe.full_sync(symbols, timeframes, start=start, end=end)
    total = sum(results.values())
    print(f"\n✅ 同步完成，共 {total} 根 K 线")


def cmd_update():
    """增量更新数据"""
    cfg = load_config()
    pipe = get_pipeline()
    symbols = cfg.get("symbols", ["BTC/USDT"])
    timeframes = cfg.get("timeframes", ["1h"])

    print(f"🔄 增量更新")
    total = 0
    for sym in symbols:
        for tf in timeframes:
            n = pipe.incremental_update(sym, tf)
            total += n
    print(f"\n✅ 增量更新完成，新增 {total} 根 K 线")


def cmd_run():
    """运行回测"""
    cfg = load_config()
    store = get_store()
    bt_cfg = cfg.get("backtest", {})

    from backtest.runner import BacktestRunner
    from strategies.examples.ema_short import EMAShort, EMAShortConfig
    from backtest.adapter import create_crypto_instrument, kline_to_bar_type
    from analysis.report import generate_html_report
    from decimal import Decimal

    # 寻优最优 DOGE EMA(30,150) —— 1h +8.19% 盈亏比1.58 100笔 回撤8.2%
    # 备选 BTC EMA(20,200) +2.31% / BNB EMA(20,50) +3.59%，但 DOGE 显著更优
    symbol = "DOGE/USDT"
    timeframe = "1h"
    instrument = create_crypto_instrument(symbol)
    bar_type = kline_to_bar_type(symbol, "BINANCE", timeframe)

    strategy = EMAShort(
        EMAShortConfig(
            instrument_id=instrument.id,
            bar_type=bar_type,
            trade_size=Decimal("5"),
            fast_ema_period=30,
            slow_ema_period=150,
        ),
    )

    # 运行
    runner = BacktestRunner(store)
    result = runner.run(
        symbol=symbol,
        timeframe=timeframe,
        strategy=strategy,
        start=bt_cfg.get("start"),
        end=bt_cfg.get("end"),
    )

    # 生成报告
    report_path = generate_html_report(result)

    # 打印摘要
    reports = result["reports"]
    print(f"\n📊 回测完成")
    print(f"   {report_path}")
    runner.dispose()


def cmd_status():
    """查看数据状态"""
    store = get_store()
    status = store.get_data_status()
    if status.empty:
        print("📭 数据库为空，请先运行 sync")
        return
    print(f"\n📊 数据状态 ({len(status)} 条记录)")
    print(status.to_string(index=False))


def cmd_quality():
    """查看数据质量报告"""
    store = get_store()
    quality = store.get_quality_log()
    if quality.empty:
        print("📭 无质量日志")
        return
    print(f"\n🔍 数据质量日志 ({len(quality)} 条)")
    print(quality.to_string(index=False))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]
    commands = {
        "sync": cmd_sync,
        "update": cmd_update,
        "run": cmd_run,
        "status": cmd_status,
        "quality": cmd_quality,
    }

    fn = commands.get(cmd)
    if fn is None:
        print(f"未知命令: {cmd}")
        print(__doc__)
        return

    fn()


if __name__ == "__main__":
    main()