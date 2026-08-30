---
name: crypto-market
description: >-
  Fetches live cryptocurrency prices, market data, historical trends, and comparative analysis.
  Use when the user asks about crypto prices, coin values, market cap, trading volume, price
  history, portfolio tracking, or wants to compare cryptocurrencies. Supports Bitcoin (BTC),
  Ethereum (ETH), Solana (SOL), and all major coins via the CoinGecko public API. Outputs
  structured JSON for easy parsing and integration.
license: MIT
compatibility: Requires Python 3.8+ with requests library and internet access
metadata:
  author: jake2
  version: "1.0"
allowed-tools: Bash(python:*) Read
---

# Crypto Market Data

Give any AI agent the ability to fetch live cryptocurrency market data, analyze price trends, and generate structured reports.

## Setup

Install dependencies first:

```bash
pip install -r scripts/requirements.txt
```

## Quick Start

**Get current prices:**
```bash
python scripts/fetch_prices.py --coins bitcoin,ethereum
```

**Get market overview (top coins):**
```bash
python scripts/market_overview.py --top 10
```

**Get price history with trend analysis:**
```bash
python scripts/price_history.py --coin bitcoin --days 30 --analysis
```

**Compare multiple coins:**
```bash
python scripts/coin_compare.py --coins bitcoin,ethereum,solana
```

## Decision Tree

Use this to pick the right script:

1. **User wants current price(s)** → `scripts/fetch_prices.py`
2. **User wants a market overview or top coins** → `scripts/market_overview.py`
3. **User wants historical data or trend analysis** → `scripts/price_history.py`
4. **User wants to compare coins side by side** → `scripts/coin_compare.py`

## Important Notes

- **Always run scripts with `--help` first** to see all available options.
- All scripts output **JSON to stdout** — parse the output directly.
- Coin IDs are slugs, not ticker symbols: use `bitcoin` not `BTC`, `ethereum` not `ETH`.
- See [references/REFERENCE.md](references/REFERENCE.md) for the full coin ID mapping and API details.
- See [references/EXAMPLES.md](references/EXAMPLES.md) for example workflows and sample outputs.

## Common Pitfalls

- **Wrong coin ID**: Use `bitcoin` not `btc`. Run `scripts/fetch_prices.py --list-coins` to search for coin IDs.
- **Rate limiting**: CoinGecko free tier allows ~30 calls/minute. Space out large batch requests.
- **Historical data**: Free tier supports up to 365 days of history.
- **Currency codes**: Use lowercase ISO codes: `usd`, `eur`, `gbp`, etc.

## Dependencies

- `requests` — HTTP client for API calls
- Python 3.8+
- Internet access (CoinGecko public API, no API key required)
