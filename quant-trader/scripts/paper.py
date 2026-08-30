#!/usr/bin/env python
"""模拟交易 —— 真正的策略运行方式

每次只处理最新 1 根 K 线，基于当前持仓状态做决策。
状态持久化到 state.json，下次接着跑。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd
import numpy as np

from data.store import MarketStore
from data.collector import BinanceCollector
from data.symbols import load_config

STATE_FILE = Path("paper_state.json")
LOG_FILE = Path("paper_trading.log")
SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"
CAPITAL = 100.0
TRADE_SIZE = 3.0  # 每笔 USDT
FAST_EMA = 50
SLOW_EMA = 200


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_state() -> dict:
    """加载持久化状态"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "balance": CAPITAL,
        "position": None,  # None=空仓, {"qty": 0.0, "entry_price": 0.0}
        "trades": 0,
        "last_processed": None,
    }


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def calc_ema(values: list[float], period: int) -> list[float | None]:
    """计算 EMA"""
    if len(values) < period:
        return [None] * len(values)
    result = [None] * (period - 1)
    # 初始 SMA
    sma = sum(values[:period]) / period
    result.append(sma)
    multiplier = 2 / (period + 1)
    for i in range(period, len(values)):
        ema = (values[i] - result[-1]) * multiplier + result[-1]
        result.append(ema)
    return result


def main():
    print("=" * 50)
    print("模拟交易 · 增量运行")
    print("=" * 50)

    cfg = load_config()
    state = load_state()

    # 1. 拉最新数据
    store = MarketStore("data/market_data.duckdb")
    collector = BinanceCollector(
        market_type="spot",
        proxy=cfg.get("exchange", {}).get("proxy"),
    )

    # 只拉最新几根 K 线（比最新多拿 200 根用于计算指标）
    latest_in_db = store.get_latest_timestamp(SYMBOL, TIMEFRAME)
    extra = 210  # 多拿一些确保指标算得稳
    since = datetime.now(timezone.utc) - timedelta(hours=extra)
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"\n[1] 拉取最新数据（最近 {extra} 根）...")
    # 直接从币安拉最新的
    df = collector.fetch_klines(SYMBOL, TIMEFRAME, start=since_str)
    if df.empty:
        print("❌ 无数据")
        store.close()
        return

    # 写入去重
    store.write_kline(df)
    df = store.query_kline(SYMBOL, TIMEFRAME, start=since_str)
    print(f"    {len(df)} 根 K 线, {df['timestamp'].min():%Y-%m-%d} ~ {df['timestamp'].max():%Y-%m-%d}")

    # 2. 计算指标
    closes = df["close"].astype(float).tolist()
    timestamps = df["timestamp"].tolist()

    fast_ema = calc_ema(closes, FAST_EMA)
    slow_ema = calc_ema(closes, SLOW_EMA)

    # 最新一根 K 线
    latest_close = closes[-1]
    latest_ts = str(timestamps[-1])
    latest_fast = fast_ema[-1]
    latest_slow = slow_ema[-1]

    # 前一根的 EMA 值（判断交叉）
    prev_fast = fast_ema[-2] if len(fast_ema) >= 2 else None
    prev_slow = slow_ema[-2] if len(slow_ema) >= 2 else None

    if latest_fast is None or latest_slow is None:
        print("⚠️ 指标尚未初始化，数据不足")
        store.close()
        return

    # 检查是否已经处理过这根 K 线
    last_processed = state.get("last_processed")
    if last_processed == latest_ts:
        print("ℹ️ 最新 K 线已处理过，无新信号")
        pos = state.get("position")
        bal = state.get("balance", CAPITAL)
        pnl = bal - CAPITAL
        pos_str = f"📈 持仓中 (入场价: {pos['entry_price']})" if pos else "📉 空仓"
        log(f"余额: ${bal:.2f} | 盈亏: ${pnl:+.2f} ({pnl/CAPITAL*100:+.2f}%) | {pos_str}")
        store.close()
        return

    # 3. 判断信号（EMA趋势策略逻辑）
    current_position = state.get("position")
    balance = state.get("balance", CAPITAL)
    trades = state.get("trades", 0)

    # 只要 EMA50 >= EMA200 且空仓 → 买入
    # 只要 EMA50 < EMA200 且有持仓 → 卖出
    should_buy = latest_fast >= latest_slow and current_position is None
    should_sell = latest_fast < latest_slow and current_position is not None

    # 计算当前价格对应的数量
    price = latest_close

    signal = "无操作"
    if should_buy:
        # 买入
        qty = TRADE_SIZE / price
        commission = TRADE_SIZE * 0.001
        state["position"] = {"qty": round(qty, 8), "entry_price": round(price, 2)}
        state["balance"] = round(balance - TRADE_SIZE - commission, 2)
        state["trades"] = trades + 1
        signal = f"📈 买入！{TRADE_SIZE} USDT → {qty:.6f} BTC @ ${price:,.2f}"
        log(signal)

    elif should_sell:
        # 卖出
        entry = current_position["entry_price"]
        qty = current_position["qty"]
        proceeds = qty * price
        commission = proceeds * 0.001
        pnl_trade = proceeds - qty * entry - commission
        state["balance"] = round(balance + proceeds - commission, 2)
        state["position"] = None
        state["trades"] = trades + 1
        signal = f"📉 卖出！{qty:.6f} BTC @ ${price:,.2f} | 本轮盈亏: ${pnl_trade:+.2f}"
        log(signal)

    # 更新最后处理时间
    state["last_processed"] = latest_ts
    save_state(state)

    # 4. 输出摘要
    pos = state.get("position")
    bal = state.get("balance", CAPITAL)
    pnl = bal - CAPITAL
    pos_str = f"📈 持仓中 (入场价: {pos['entry_price']})" if pos else "📉 空仓"

    print(f"\n{'='*50}")
    print(f"📊 当前状态")
    print(f"  余额: ${bal:.2f}")
    print(f"  盈亏: ${pnl:+.2f} ({pnl/CAPITAL*100:+.2f}%)")
    print(f"  状态: {pos_str}")
    print(f"  交易次数: {state.get('trades', 0)}")
    print(f"  EMA({FAST_EMA}): {latest_fast:.2f} | EMA({SLOW_EMA}): {latest_slow:.2f}")
    print(f"  最新信号: {signal}")
    print(f"{'='*50}")

    store.close()


if __name__ == "__main__":
    main()