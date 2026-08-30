#!/usr/bin/env python3
"""Get a market overview of top cryptocurrencies from CoinGecko."""

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


def get_market_overview(top_n=10, currency="usd", sort_by="market_cap_desc"):
    """Fetch top N coins by market cap."""
    params = {
        "vs_currency": currency,
        "order": sort_by,
        "per_page": top_n,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "1h,24h,7d",
    }
    resp = api_get(f"{API_BASE}/coins/markets", params)
    raw = resp.json()

    results = []
    for coin in raw:
        results.append({
            "rank": coin.get("market_cap_rank"),
            "id": coin["id"],
            "symbol": coin["symbol"].upper(),
            "name": coin["name"],
            "price": coin.get("current_price"),
            "market_cap": coin.get("market_cap"),
            "volume_24h": coin.get("total_volume"),
            "change_1h_pct": coin.get("price_change_percentage_1h_in_currency"),
            "change_24h_pct": coin.get("price_change_percentage_24h_in_currency"),
            "change_7d_pct": coin.get("price_change_percentage_7d_in_currency"),
            "high_24h": coin.get("high_24h"),
            "low_24h": coin.get("low_24h"),
            "circulating_supply": coin.get("circulating_supply"),
        })

    return results


def get_global_stats():
    """Fetch global crypto market statistics."""
    resp = api_get(f"{API_BASE}/global", {})
    data = resp.json()["data"]
    return {
        "total_market_cap_usd": data.get("total_market_cap", {}).get("usd"),
        "total_volume_24h_usd": data.get("total_volume", {}).get("usd"),
        "btc_dominance_pct": data.get("market_cap_percentage", {}).get("btc"),
        "eth_dominance_pct": data.get("market_cap_percentage", {}).get("eth"),
        "active_cryptocurrencies": data.get("active_cryptocurrencies"),
        "markets": data.get("markets"),
        "market_cap_change_24h_pct": data.get("market_cap_change_percentage_24h_usd"),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Get a market overview of top cryptocurrencies."
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of top coins to show (default: 10, max: 250)",
    )
    parser.add_argument(
        "--currency",
        type=str,
        default="usd",
        help="Target currency code (default: usd)",
    )
    parser.add_argument(
        "--sort",
        type=str,
        default="market_cap_desc",
        choices=[
            "market_cap_desc", "market_cap_asc",
            "volume_desc", "volume_asc",
            "id_desc", "id_asc",
        ],
        help="Sort order (default: market_cap_desc)",
    )
    parser.add_argument(
        "--global-stats",
        action="store_true",
        help="Include global market statistics",
    )

    args = parser.parse_args()

    output = {}

    if args.global_stats:
        output["global"] = get_global_stats()

    output["coins"] = get_market_overview(args.top, args.currency, args.sort)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
