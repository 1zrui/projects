"""nautilus_trader 适配器 —— 数据转换 + 交易品种工厂

将 DuckDB 中的 K 线数据转换为 nautilus_trader 的 Bar 对象，
并提供加密货币交易品种（CurrencyPair）的工厂方法。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pandas as pd
from nautilus_trader.model.currencies import BTC, BNB, DOGE, ETH, SOL, USDT
from nautilus_trader.model.data import BarType
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments.currency_pair import CurrencyPair
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.persistence.wranglers import BarDataWrangler

# 预定义交易对信息
SYMBOL_SPECS: dict[str, dict[str, Any]] = {
    "BTC/USDT": {
        "base": BTC,
        "quote": USDT,
        "price_precision": 2,
        "size_precision": 6,
        "price_increment": 1,
        "price_prec": 2,
        "size_increment": 1,
        "size_prec": 6,
        "min_notional": 10.0,
        "max_notional": 10_000_000.0,
    },
    "ETH/USDT": {
        "base": ETH,
        "quote": USDT,
        "price_precision": 2,
        "size_precision": 5,
        "price_increment": 1,
        "price_prec": 2,
        "size_increment": 1,
        "size_prec": 5,
        "min_notional": 10.0,
        "max_notional": 5_000_000.0,
    },
    "SOL/USDT": {
        "base": SOL,
        "quote": USDT,
        "price_precision": 2,
        "size_precision": 2,
        "price_increment": 1,
        "price_prec": 2,
        "size_increment": 1,
        "size_prec": 2,
        "min_notional": 10.0,
        "max_notional": 3_000_000.0,
    },
    "BNB/USDT": {
        "base": BNB,
        "quote": USDT,
        "price_precision": 2,
        "size_precision": 4,
        "price_increment": 1,
        "price_prec": 2,
        "size_increment": 1,
        "size_prec": 4,
        "min_notional": 10.0,
        "max_notional": 3_000_000.0,
    },
    "DOGE/USDT": {
        "base": DOGE,
        "quote": USDT,
        "price_precision": 5,
        "size_precision": 1,
        "price_increment": 1,
        "price_prec": 5,
        "size_increment": 1,
        "size_prec": 1,
        "min_notional": 10.0,
        "max_notional": 3_000_000.0,
    },
}

# 粒度映射：nautilus_trader 的 BarSpecification 格式
TIMEFRAME_MAP = {
    "1m": "1-MINUTE",
    "5m": "5-MINUTE",
    "15m": "15-MINUTE",
    "30m": "30-MINUTE",
    "1h": "1-HOUR",
    "2h": "2-HOUR",
    "4h": "4-HOUR",
    "6h": "6-HOUR",
    "8h": "8-HOUR",
    "12h": "12-HOUR",
    "1d": "1-DAY",
}


def create_crypto_instrument(
    symbol: str,
    venue_name: str = "BINANCE",
) -> CurrencyPair:
    """创建加密货币交易品种

    Args:
        symbol: 交易对，如 'BTC/USDT'
        venue_name: 交易所名称，默认 BINANCE
    Returns:
        nautilus_trader CurrencyPair 对象
    """
    specs = SYMBOL_SPECS.get(symbol)
    if specs is None:
        raise ValueError(f"不支持的交易对: {symbol}，可用: {list(SYMBOL_SPECS)}")

    normalized = symbol.replace("/", "")
    instrument_id = InstrumentId(
        symbol=Symbol(normalized),
        venue=Venue(venue_name),
    )

    return CurrencyPair(
        instrument_id=instrument_id,
        raw_symbol=Symbol(normalized),
        base_currency=specs["base"],
        quote_currency=specs["quote"],
        price_precision=specs["price_precision"],
        size_precision=specs["size_precision"],
        price_increment=Price(specs["price_increment"], specs["price_prec"]),
        size_increment=Quantity(specs["size_increment"], specs["size_prec"]),
        margin_init=Decimal("0.05"),
        margin_maint=Decimal("0.025"),
        maker_fee=Decimal("0.001"),
        taker_fee=Decimal("0.001"),
        ts_event=0,
        ts_init=0,
    )


def kline_to_bar_type(
    symbol: str,
    venue_name: str,
    timeframe: str,
) -> BarType:
    """将交易对+粒度转换为 nautilus BarType 字符串

    Examples:
        'BTC/USDT', 'BINANCE', '1h' → 'BTCUSDT.BINANCE-1-HOUR-LAST-EXTERNAL'
    """
    normalized = symbol.replace("/", "")
    tf_str = TIMEFRAME_MAP.get(timeframe, timeframe)
    bar_type_str = f"{normalized}.{venue_name}-{tf_str}-LAST-EXTERNAL"
    return BarType.from_str(bar_type_str)


def kline_df_to_bars(
    df: pd.DataFrame,
    instrument: CurrencyPair,
    bar_type: BarType,
) -> list[Any]:
    """将 K 线 DataFrame 转换为 nautilus Bar 列表

    Args:
        df: 必须包含列 [timestamp, open, high, low, close, volume]
        instrument: 对应的交易品种
        bar_type: 对应的 BarType
    Returns:
        list[Bar]
    """
    required = ["timestamp", "open", "high", "low", "close", "volume"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"DataFrame 缺少列: {col}")

    bar_cols = ["open", "high", "low", "close"]
    if "volume" in df.columns:
        bar_cols.append("volume")
    df_out = df[bar_cols].copy()
    df_out.index = df["timestamp"].copy()
    df_out.index.name = "timestamp"
    for col in df_out.columns:
        if hasattr(df_out[col], "values"):
            df_out[col] = df_out[col].values.copy()

    wrangler = BarDataWrangler(bar_type=bar_type, instrument=instrument)
    return wrangler.process(df_out)


def parse_bar_type(bar_type_str: str) -> tuple[str, str]:
    """从 BarType 字符串解析交易对和粒度（反向解析）"""
    parts = bar_type_str.split(".")
    symbol_raw = parts[0]
    if "USDT" in symbol_raw:
        base = symbol_raw.replace("USDT", "")
        symbol = f"{base}/USDT"
    else:
        symbol = symbol_raw

    agg_part = parts[1] if len(parts) > 1 else ""
    rev_map = {v: k for k, v in TIMEFRAME_MAP.items()}
    for ntf, fmt in rev_map.items():
        if fmt in agg_part:
            return symbol, ntf

    return symbol, "1h"
