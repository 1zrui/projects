---
name: crypto-market-analysis
description: >-
  Analyze crypto trends, not trade.
category: quant-trading
version: 1.1.0
author: curated (+ Hermes session 2026-08-27)
license: MIT
metadata:
  hermes:
    tags: [crypto, analysis, technical-analysis, market-data, mcps, github-discovery]
    related_skills: [crypto-trend-analyzer, quant-trading, quant-trading-strategy]
---

# Crypto Market Analysis

Use when the user asks about **analyzing** crypto market trends, price action, technical indicators, or market sentiment — **not** when they want to execute trades, backtest strategies, or run trading bots. Those are covered by `quant-trading` and `quant-trading-strategy`.

## When to Use
- User says "分析走势" / "看看 ETH/BTC" / "分析货币走势" → analysis, NOT trading.
- User asks to *find* a crypto-analysis skill or GitHub project (use `references/github-crypto-skills.md`).
- Need a methodology index (TA indicators, multi-source confluence, on-chain/sentiment tools) rather than a hands-on run.
- For a ready-to-run Binance K-line analyzer, prefer the sibling `crypto-trend-analyzer` skill.

## Core Distinction

| Class | What it does | Tools |
|-------|-------------|-------|
| **Crypto Market Analysis** (this skill) | Understand trends, read indicators, assess market state | TA libraries, chart tools, data sources |
| **Quant Trading** (`quant-trading`) | Backtest strategies, execute trades | vectorbt, ccxt, backtesting engines |

**Never** confuse the two. If the user says "分析走势" / "分析货币走势", they want *analysis*, not *trading*. Do not search for trading bots, execution frameworks, or automated trading systems.

## Where to Find Crypto Analysis Projects on GitHub

### Technical Analysis Indicators
- **ta-lib/ta-lib-python** (⭐12k) — 200+ indicators (RSI, MACD, Bollinger, etc.). Gold standard.
- **talipp** (534⭐) — Incremental TA lib, real-time streaming updates, no full data reload.
- **CryptoSignal/Crypto-Signal** (5.6k⭐) — 50+ indicators, generates buy/sell signals, data-focused.

### MCP-Enabled Analysis Tools (AI-accessible)
- **atilaahmettaner/tradingview-mcp** (4.1k⭐) — TradingView data + TA via MCP protocol. Best for Hermes integration.
- **kukapay/crypto-indicators-mcp** (130⭐) — MCP indicator server (RSI, MACD, EMA).
- **truss44/mcp-crypto-price** (39⭐) — Real-time price analysis via CoinCap.

### Visualization & Dashboards
- **prouast/cryptocurrency-analysis** (293⭐) — R-based market analysis + visualization.
- **sajanpoudel/CryptoSensei** (20⭐) — TA + sentiment analysis + visualization platform.

### On-Chain & Sentiment Analysis
- **santiment/sanpy** — On-chain data + social sentiment.
- **elfa-ai/claude-ai-trading-skill** (13⭐) — Social sentiment + trending token queries.

## How to Analyze Crypto Trends

### Step 1: Get Live Data
- **CoinGecko API** (free, no key needed): `api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd&include_24hr_change=true`
- **ccxt** (⭐43k) — Unified exchange API, supports 100+ exchanges.
- **TradingView MCP** — Real-time data via MCP (best for AI integration).

### Step 2: Apply Technical Indicators
- Price action: support/resistance, trendlines
- Volume analysis: volume profile, OBV
- Momentum: RSI, Stochastic, MACD, WillR, CCI
- Volatility: Bollinger Bands, ATR
- Market structure: higher highs/lows, trend regime classification

### Step 3: Cross-Reference Data Sources
- **Price action** + **Volume** + **On-chain metrics** + **Sentiment** = robust analysis
- Don't rely on a single indicator; look for confluence.

### Step 4: Watch for Catalysts
- Macro: Fed policy, Treasury yields, USD strength
- Regulation: CLARITY Act, SEC actions, pro-crypto legislation
- On-chain: ETF flows, whale movements, staking rates
- Market structure: liquidation cascades, open interest, funding rates

## Pitfalls
- ❌ Don't confuse analysis tools with trading bots. The user will correct you.
- ❌ Don't recommend backtesting frameworks when the user just wants to *read the market*.
- ❌ Price prediction ML models are mostly noise — flag them as entertainment, not analysis.
- ✅ MCP-enabled tools are the best path for Hermes integration.
- ⚠️ **Delivery channel matters (2026-08-27 lesson).** If you also use the local `crypto-trend-analyzer` skill, note its card-delivery steps are written for the **NapCat** channel (copy to `Downloads` + NapCat `send_private_msg` + `file:///`). The active session may instead be on the official **qqbot** platform (openid like `ADA809A2441B9620CB07A76D331917DF`), where that NapCat-specific send path does not apply and markdown reports can be sent directly. **Before sending any deliverable, confirm the current session's platform/channel** and adapt — don't blindly copy another channel's send姿势.

## Verification
- After recommending a project, check its star count, last update, and language match.
- For live price checks, use CoinGecko API (free, no auth, reliable).
- Cross-reference price data from at least 2 sources before reporting.

## Finding these skills on GitHub (practical)
When the user asks you to *find* a crypto-analysis skill on GitHub (not just use a local one), see `references/github-crypto-skills.md` — it records a working `gh` CLI search path (web_search/Tavily was down this session; curl-to-github-via-proxy timed out; authenticated `gh` CLI worked) and a concrete list of crypto skills found on GitHub.
