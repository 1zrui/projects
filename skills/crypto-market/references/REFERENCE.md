# Crypto Market Skill — API Reference

## CoinGecko API

All scripts use the [CoinGecko API v3](https://www.coingecko.com/en/api/documentation) (free tier, no API key required).

### Rate Limits

- **Free tier**: ~30 requests/minute
- If rate-limited, wait 60 seconds before retrying
- Batch multiple coin queries into single requests when possible (all scripts support comma-separated coin IDs)

### Common Coin IDs

| Coin | ID | Symbol |
|------|-----|--------|
| Bitcoin | `bitcoin` | BTC |
| Ethereum | `ethereum` | ETH |
| Solana | `solana` | SOL |
| Cardano | `cardano` | ADA |
| Dogecoin | `dogecoin` | DOGE |
| Polkadot | `polkadot` | DOT |
| Chainlink | `chainlink` | LINK |
| Avalanche | `avalanche-2` | AVAX |
| Polygon | `matic-network` | MATIC |
| Ripple | `ripple` | XRP |
| Litecoin | `litecoin` | LTC |
| Uniswap | `uniswap` | UNI |
| Cosmos | `cosmos` | ATOM |
| Near Protocol | `near` | NEAR |
| Aptos | `aptos` | APT |

**Note**: Some coin IDs are not intuitive (e.g., Avalanche is `avalanche-2`, Polygon is `matic-network`). Use `fetch_prices.py --list-coins <query>` to search for the correct ID.

### Supported Currencies

Use lowercase ISO 4217 codes: `usd`, `eur`, `gbp`, `jpy`, `cad`, `aud`, `chf`, `cny`, `krw`, `inr`, `brl`, `mxn`, `rub`, `try`, `zar`, `sek`, `nok`, `dkk`, `pln`, `thb`, `idr`, `huf`, `czk`, `php`, `sgd`, `twd`, `nzd`

Also supports crypto base currencies: `btc`, `eth`, `bnb`, `sol`

### Historical Data Limits

| Days | Data Granularity |
|------|-----------------|
| 1 | 5-minute intervals |
| 2-90 | Hourly intervals |
| 91-365 | Daily intervals |
| >365 | Not available on free tier |

## Script Outputs

All scripts output JSON to stdout. Errors are also returned as JSON with an `"error"` key.

### fetch_prices.py Output Schema

```json
{
  "bitcoin": {
    "price": 98234.56,
    "market_cap": 1930000000000,
    "volume_24h": 45000000000,
    "change_24h_pct": 2.34
  }
}
```

### market_overview.py Output Schema

```json
{
  "global": { "total_market_cap_usd": ..., "btc_dominance_pct": ... },
  "coins": [
    { "rank": 1, "id": "bitcoin", "symbol": "BTC", "price": ..., ... }
  ]
}
```

### price_history.py Output Schema

```json
{
  "coin": "bitcoin",
  "days": 30,
  "analysis": {
    "direction": "uptrend",
    "change_pct": 12.5,
    "volatility_label": "moderate",
    ...
  },
  "prices": [{ "timestamp": 1708300800, "price": 95000.0 }, ...],
  "volumes": [{ "timestamp": 1708300800, "volume": 40000000000 }, ...]
}
```

### coin_compare.py Output Schema

```json
{
  "coins": [{ "id": "bitcoin", "symbol": "BTC", "price": ..., ... }],
  "summary": {
    "best_performer_24h": { "id": "ethereum", "change_pct": 5.2 },
    "worst_performer_24h": { "id": "bitcoin", "change_pct": -1.1 },
    ...
  }
}
```
