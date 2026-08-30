#!/usr/bin/env python3
"""Fetch current cryptocurrency prices from CoinGecko."""

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


def search_coins(query):
    """Search for coin IDs matching a query string."""
    resp = api_get(f"{API_BASE}/search", {"query": query})
    data = resp.json()
    results = []
    for coin in data.get("coins", [])[:15]:
        results.append({
            "id": coin["id"],
            "symbol": coin["symbol"],
            "name": coin["name"],
            "market_cap_rank": coin.get("market_cap_rank"),
        })
    return results


def fetch_prices(coin_ids, currency="usd", include_24h_change=False):
    """Fetch current prices for a list of coin IDs."""
    params = {
        "ids": ",".join(coin_ids),
        "vs_currencies": currency,
        "include_market_cap": "true",
        "include_24hr_vol": "true",
    }
    if include_24h_change:
        params["include_24hr_change"] = "true"

    resp = api_get(f"{API_BASE}/simple/price", params)
    raw = resp.json()

    result = {}
    for coin_id in coin_ids:
        if coin_id not in raw:
            result[coin_id] = {"error": f"Coin '{coin_id}' not found. Use --list-coins to search."}
            continue
        coin_data = raw[coin_id]
        entry = {
            "price": coin_data.get(currency),
            "market_cap": coin_data.get(f"{currency}_market_cap"),
            "volume_24h": coin_data.get(f"{currency}_24h_vol"),
        }
        if include_24h_change:
            entry["change_24h_pct"] = coin_data.get(f"{currency}_24h_change")
        result[coin_id] = entry

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Fetch current cryptocurrency prices from CoinGecko."
    )
    parser.add_argument(
        "--coins",
        type=str,
        help="Comma-separated coin IDs (e.g., bitcoin,ethereum,solana)",
    )
    parser.add_argument(
        "--currency",
        type=str,
        default="usd",
        help="Target currency code (default: usd)",
    )
    parser.add_argument(
        "--include-24h-change",
        action="store_true",
        help="Include 24-hour price change percentage",
    )
    parser.add_argument(
        "--list-coins",
        type=str,
        metavar="QUERY",
        help="Search for coin IDs matching a query (e.g., --list-coins bitcoin)",
    )

    args = parser.parse_args()

    if args.list_coins:
        results = search_coins(args.list_coins)
        print(json.dumps(results, indent=2))
        return

    if not args.coins:
        parser.error("--coins is required (or use --list-coins to search)")

    coin_ids = [c.strip().lower() for c in args.coins.split(",")]
    result = fetch_prices(coin_ids, args.currency, args.include_24h_change)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
