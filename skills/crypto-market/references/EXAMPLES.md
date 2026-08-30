# Example Workflows

## 1. Quick Price Check

**User says**: "What's the current price of Bitcoin and Ethereum?"

```bash
python scripts/fetch_prices.py --coins bitcoin,ethereum --include-24h-change
```

## 2. Daily Market Briefing

**User says**: "Give me a market overview"

```bash
python scripts/market_overview.py --top 10 --global-stats
```

This returns the top 10 coins with 1h/24h/7d price changes plus global market stats (total market cap, BTC dominance, etc.).

## 3. Investment Research

**User says**: "How has Solana been performing this month?"

```bash
python scripts/price_history.py --coin solana --days 30 --analysis
```

For a summary without raw data:

```bash
python scripts/price_history.py --coin solana --days 30 --analysis --no-raw-data
```

## 4. Coin Comparison

**User says**: "Compare Bitcoin, Ethereum, and Solana"

```bash
python scripts/coin_compare.py --coins bitcoin,ethereum,solana
```

Returns side-by-side metrics and a summary of which coin is performing best/worst.

## 5. Finding a Coin ID

**User says**: "What's the price of AVAX?"

First, find the correct coin ID:

```bash
python scripts/fetch_prices.py --list-coins avalanche
```

Then fetch the price using the returned ID:

```bash
python scripts/fetch_prices.py --coins avalanche-2
```

## 6. Multi-Currency Pricing

**User says**: "What's Bitcoin worth in euros?"

```bash
python scripts/fetch_prices.py --coins bitcoin --currency eur
```

## 7. Trend Analysis Pipeline

For a complete analysis report, combine scripts:

1. Get current prices: `python scripts/fetch_prices.py --coins bitcoin,ethereum,solana --include-24h-change`
2. Get 30-day trends: `python scripts/price_history.py --coin bitcoin --days 30 --analysis --no-raw-data`
3. Compare performance: `python scripts/coin_compare.py --coins bitcoin,ethereum,solana`

Use the combined output to generate a comprehensive market report.
