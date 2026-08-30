#!/usr/bin/env python3
"""Compare multiple cryptocurrencies side by side using CoinGecko data."""

import argparse
import json
import sys
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


def compare_coins(coin_ids, currency="usd"):
    """Fetch and compare market data for multiple coins."""
    params = {
        "vs_currency": currency,
        "ids": ",".join(coin_ids),
        "order": "market_cap_desc",
        "sparkline": "false",
        "price_change_percentage": "1h,24h,7d,30d",
    }
    resp = api_get(f"{API_BASE}/coins/markets", params)
    raw = resp.json()

    coins = []
    for coin in raw:
        coins.append({
            "id": coin["id"],
            "symbol": coin["symbol"].upper(),
            "name": coin["name"],
            "rank": coin.get("market_cap_rank"),
            "price": coin.get("current_price"),
            "market_cap": coin.get("market_cap"),
            "volume_24h": coin.get("total_volume"),
            "change_1h_pct": coin.get("price_change_percentage_1h_in_currency"),
            "change_24h_pct": coin.get("price_change_percentage_24h_in_currency"),
            "change_7d_pct": coin.get("price_change_percentage_7d_in_currency"),
            "change_30d_pct": coin.get("price_change_percentage_30d_in_currency"),
            "high_24h": coin.get("high_24h"),
            "low_24h": coin.get("low_24h"),
            "ath": coin.get("ath"),
            "ath_change_pct": coin.get("ath_change_percentage"),
            "circulating_supply": coin.get("circulating_supply"),
            "total_supply": coin.get("total_supply"),
            "max_supply": coin.get("max_supply"),
        })

    # Build comparison summary
    if len(coins) >= 2:
        best_24h = max(coins, key=lambda c: c.get("change_24h_pct") or -999)
        worst_24h = min(coins, key=lambda c: c.get("change_24h_pct") or 999)
        highest_volume = max(coins, key=lambda c: c.get("volume_24h") or 0)
        largest_market_cap = max(coins, key=lambda c: c.get("market_cap") or 0)

        summary = {
            "best_performer_24h": {"id": best_24h["id"], "change_pct": best_24h.get("change_24h_pct")},
            "worst_performer_24h": {"id": worst_24h["id"], "change_pct": worst_24h.get("change_24h_pct")},
            "highest_volume": {"id": highest_volume["id"], "volume": highest_volume.get("volume_24h")},
            "largest_market_cap": {"id": largest_market_cap["id"], "market_cap": largest_market_cap.get("market_cap")},
        }
    else:
        summary = None

    return {"coins": coins, "summary": summary}


def main():
    parser = argparse.ArgumentParser(
        description="Compare multiple cryptocurrencies side by side."
    )
    parser.add_argument(
        "--coins",
        type=str,
        required=True,
        help="Comma-separated coin IDs (e.g., bitcoin,ethereum,solana)",
    )
    parser.add_argument(
        "--currency",
        type=str,
        default="usd",
        help="Target currency code (default: usd)",
    )

    args = parser.parse_args()

    coin_ids = [c.strip().lower() for c in args.coins.split(",")]
    if len(coin_ids) < 2:
        print(json.dumps({"error": "Provide at least 2 coins to compare"}))
        sys.exit(1)

    result = compare_coins(coin_ids, args.currency)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
