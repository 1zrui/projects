#!/usr/bin/env python3
"""Fetch historical price data and trend analysis from CoinGecko."""

import argparse
import json
import time
import requests

API_BASE = "https://api.coingecko.com/api/v3"
HEADERS = {"User-Agent": "crypto-market-agent-skill/1.0"}


def api_get(url, params):
    """GET with automatic retry on rate limit (429)."""
    for attempt in range(3):
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        if resp.status_code == 429:
            time.sleep(15 * (attempt + 1))
            continue
        resp.raise_for_status()
        return resp
    resp.raise_for_status()


def fetch_history(coin_id, days=30, currency="usd"):
    """Fetch historical price data for a coin."""
    params = {
        "vs_currency": currency,
        "days": days,
    }
    resp = api_get(f"{API_BASE}/coins/{coin_id}/market_chart", params)
    raw = resp.json()

    prices = []
    for timestamp_ms, price in raw.get("prices", []):
        prices.append({
            "timestamp": int(timestamp_ms / 1000),
            "price": price,
        })

    volumes = []
    for timestamp_ms, vol in raw.get("total_volumes", []):
        volumes.append({
            "timestamp": int(timestamp_ms / 1000),
            "volume": vol,
        })

    return {"prices": prices, "volumes": volumes}


def analyze_trend(prices):
    """Compute basic trend analysis from price data."""
    if not prices:
        return {"error": "No price data available"}

    values = [p["price"] for p in prices]
    current = values[-1]
    start = values[0]
    high = max(values)
    low = min(values)
    avg = sum(values) / len(values)
    change_pct = ((current - start) / start) * 100 if start else 0

    # Simple trend direction
    mid = len(values) // 2
    first_half_avg = sum(values[:mid]) / mid if mid else current
    second_half_avg = sum(values[mid:]) / (len(values) - mid) if (len(values) - mid) else current

    if abs(change_pct) < 3:
        direction = "sideways"
    elif change_pct > 0:
        direction = "uptrend"
    else:
        direction = "downtrend"

    # Volatility (coefficient of variation)
    variance = sum((v - avg) ** 2 for v in values) / len(values)
    std_dev = variance ** 0.5
    volatility_pct = (std_dev / avg) * 100 if avg else 0

    if volatility_pct < 5:
        volatility_label = "low"
    elif volatility_pct < 15:
        volatility_label = "moderate"
    else:
        volatility_label = "high"

    return {
        "direction": direction,
        "change_pct": round(change_pct, 2),
        "current_price": round(current, 6),
        "period_high": round(high, 6),
        "period_low": round(low, 6),
        "average_price": round(avg, 6),
        "volatility_pct": round(volatility_pct, 2),
        "volatility_label": volatility_label,
        "data_points": len(values),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Fetch historical crypto price data with optional trend analysis."
    )
    parser.add_argument(
        "--coin",
        type=str,
        required=True,
        help="Coin ID (e.g., bitcoin, ethereum, solana)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days of history (default: 30, max: 365)",
    )
    parser.add_argument(
        "--currency",
        type=str,
        default="usd",
        help="Target currency code (default: usd)",
    )
    parser.add_argument(
        "--analysis",
        action="store_true",
        help="Include trend analysis summary",
    )
    parser.add_argument(
        "--no-raw-data",
        action="store_true",
        help="Omit raw price/volume arrays (use with --analysis for summary only)",
    )

    args = parser.parse_args()

    history = fetch_history(args.coin, args.days, args.currency)

    output = {"coin": args.coin, "days": args.days, "currency": args.currency}

    if args.analysis:
        output["analysis"] = analyze_trend(history["prices"])

    if not args.no_raw_data:
        output["prices"] = history["prices"]
        output["volumes"] = history["volumes"]

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
