"""端到端验证脚本 —— 用合成数据跑通全流程

验证链路: store → collector格式 → adapter → nautilus引擎 → 策略 → 报告
不依赖真实币安网络。
"""

from __future__ import annotations

from decimal import Decimal

import numpy as np
import pandas as pd

from analysis.report import generate_html_report
from backtest.adapter import create_crypto_instrument, kline_df_to_bars, kline_to_bar_type
from backtest.runner import BacktestRunner
from data.store import MarketStore
from strategies.examples.ema_cross import EMACross, EMACrossConfig


def gen_synthetic_data(
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
    n: int = 2000,
    seed: int = 42,
) -> pd.DataFrame:
    """生成随机游走合成 K 线数据"""
    rng = np.random.default_rng(seed)

    # 随机游走价格（带趋势段）
    price = 40000.0
    prices = []
    drift = 0.0
    for i in range(n):
        # 分段趋势
        if i % 500 == 0:
            drift = rng.normal(0, 0.0005)
        price *= 1 + drift + rng.normal(0, 0.008)
        prices.append(price)

    price_series = pd.Series(prices)
    spread = np.abs(rng.normal(0, 50, n))

    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC"),
        "open": price_series,
        "high": price_series + spread,
        "low": price_series - spread,
        "close": price_series + rng.normal(0, 1, n),
        "volume": rng.uniform(50, 500, n),
        "quote_vol": rng.uniform(2_000_000, 20_000_000, n),
        "trade_count": rng.integers(100, 5000, n).astype(float),
        "taker_buy_vol": rng.uniform(20, 300, n),
        "taker_buy_quote": rng.uniform(1_000_000, 10_000_000, n),
    })
    # 修正 high/low 合理性
    df["high"] = df[["open", "high", "close"]].max(axis=1)
    df["low"] = df[["open", "low", "close"]].min(axis=1)
    df["symbol"] = symbol
    df["timeframe"] = timeframe
    return df


def main():
    print("=" * 60)
    print("端到端验证：合成数据 → 存储 → 回测 → 报告")
    print("=" * 60)

    # 1. 生成合成数据并写入 DuckDB
    print("\n[1] 生成合成数据 ...")
    df = gen_synthetic_data()
    print(f"    生成 {len(df)} 根 1h K线")

    with MarketStore("data/test_verify.duckdb") as store:
        n = store.write_kline(df)
        print(f"[2] 写入 DuckDB: {n} 行")

        # 验证读取
        back = store.query_kline("BTC/USDT", "1h")
        print(f"[3] 读回验证: {len(back)} 行, "
              f"{back['timestamp'].min():%Y-%m-%d} ~ {back['timestamp'].max():%Y-%m-%d}")

        # 2. 创建策略
        print("\n[4] 创建 EMA 交叉策略 ...")
        instrument = create_crypto_instrument("BTC/USDT")
        bar_type = kline_to_bar_type("BTC/USDT", "BINANCE", "1h")
        strategy = EMACross(
            EMACrossConfig(
                instrument_id=instrument.id,
                bar_type=bar_type,
                trade_size=Decimal("10"),
                fast_ema_period=10,
                slow_ema_period=20,
            ),
        )

        # 3. 运行回测
        print("[5] 运行回测 ...")
        runner = BacktestRunner(store)
        result = runner.run(
            symbol="BTC/USDT",
            timeframe="1h",
            strategy=strategy,
        )
        runner.dispose()

        # 4. 生成报告
        print("[6] 生成 HTML 报告 ...")
        report_path = generate_html_report(result)
        print(f"\n✅ 报告: {report_path}")

        # 5. 摘要
        reports = result["reports"]
        config = reports["config"]
        print(f"\n{'='*60}")
        print(f"回测摘要")
        print(f"{'='*60}")
        print(f"  标的:     {config['symbol']}  {config['timeframe']}")
        print(f"  K线数:    {config['bars']}")
        for key in ["account", "positions", "fills"]:
            val = reports.get(key)
            if isinstance(val, str):
                print(f"  {key}: ⚠️ {val}")
            elif val is not None and hasattr(val, "shape"):
                print(f"  {key}: {val.shape[0]} 行")
            else:
                print(f"  {key}: (空)")
        print("\n✅ 端到端验证通过")


if __name__ == "__main__":
    main()