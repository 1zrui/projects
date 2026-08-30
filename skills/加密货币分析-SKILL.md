---
name: crypto-trend-analysis
description: "Use when user asks about crypto 走势 — prices, news, TA."
version: 1.0.0
author: hermes-agent
license: MIT
metadata:
  hermes:
    tags: [quant-trading, crypto, analysis, market]
    related_skills: [quant-trading, quant-trading-strategy]
---

# Crypto Trend & Market Analysis

大哥's crypto work shifted from quant backtesting to **行情走势分析** (trend/market analysis). Sessions like "今天加密货币怎么回事" / "ETH 怎么一直涨" / "分析下 X 走势" are this class. **Do NOT default to recommending trading bots or backtesting frameworks** — he explicitly corrected this (2026-08-20): 不是搞量化交易，是分析货币走势.

## Core workflow

**三步全做，缺一不可。** 2026-08-26 和 2026-08-30 两次实测都因跳过催化剂搜索被大哥纠正。

1. **Live price first** — real data beats memory. CoinGecko, no key needed:
   ```bash
   curl -s "https://api.coingecko.com/api/v3/simple/price?ids=ethereum,bitcoin&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true&include_market_cap=true"
   ```
2. **Catalyst search** — web_search `crypto <coin> news <date>`. Typical drivers: policy bills (CLARITY Act), ETF flows, Treasury buybacks → yield ↓ → risk-on, liquidation cascades, Fear&Greed swing. Label rumored vs confirmed.
3. **Technical analysis** — via tradingview-mcp if wired up: tools appear as `mcp_tradingview_*`. Three key tools:
   - `coin_analysis(symbol, exchange, timeframe)` — 单周期深度分析（RSI/MACD/EMA/布林带/支撑阻力）
   - `multi_timeframe_analysis(symbol, exchange)` — 多周期对齐（周线→日线→4H→1H→15m），输出综合评分和建议
   - `bitcoin_market_pulse()` — BTC宏观背景（价格/主导率/总市值/风险评估），分析任何币前先调一次
   - Full setup: `references/tradingview-mcp.md`.

## 分析输出模板

```
## [币种] 合约分析

### 📊 实时价格
- [币种]: $价格 (涨跌幅 / 24h)
- BTC: $价格 (涨跌幅)
- 市值/主导率

### 📰 催化剂（为什么涨/跌）
1. [事件1] — 影响描述
2. [事件2] — 影响描述

### 📈 技术面（多周期对齐）
| 周期 | 方向 | 关键信号 |
|------|------|----------|
| 周线 | 🟢/🔴/⚪ | ... |
| 日线 | ... | ... |
| 4小时 | ... | ... |
| 1小时 | ... | ... |

### 🎯 关键价位
| 类型 | 价位 | 距当前 |
|------|------|--------|
| 阻力1 | $xxx | +x% |
| 当前 | $xxx | — |
| 支撑1 | $xxx | -x% |

### ⚡ 合约建议
- 短线（1-4h）：...
- 中线（日线）：...
- 风险提示：...
- 结论：...
```

## GitHub project landscape (researched 2026-08-20)

- **tradingview-mcp** (atilaahmettaner, ~4.1k⭐) — primary pick: 37 tools, real-time TA, screeners, backtest, multi-exchange incl. Binance all pairs. No TradingView account/API key needed. ~100MB RAM.
- **CryptoSignal/Crypto-Signal** (~5.6k⭐) — 50+ indicator signal tool, good self-hosted fallback.
- **talipp** — incremental (streaming) TA library, lightweight.
- **crypto-indicators-mcp** (kukapay) — minimal MCP indicator server as备选.
- Data layer: ccxt for raw exchange data (esp. 合约/永续 — TradingView endpoints are spot), ta-lib-python for classic indicators.

## Pitfalls

- **步骤 2（催化剂搜索）绝不能跳过** — 2026-08-26 实测：只做了步骤 1（价格）和步骤 3（技术面），被大哥指出分析不完整。三个步骤是完整分析的最低要求，缺催化剂 = 不知道为什么涨/跌。
- `uvx --from tradingview-mcp-server tradingview-mcp` — executable is **`tradingview-mcp`**, not `tradingview-mcp-server`.
- Background terminal processes on this box do NOT inherit `~/.hermes/bin` PATH → use absolute `/home/ubuntu/.hermes/bin/uvx`. Verify with `which uvx`.
- stdio MCP server exits when stdin closes — to keep alive for memory/probe: `tail -f /dev/null | uvx ...` as background, then `ps aux | grep` for RSS (`$6/1024` MB).
- GitHub search API (unauthenticated) ≈ 10 req/min — space consecutive queries ~30s.
- TradingView endpoints are **spot** prices; Binance 永续/合约 goes through ccxt.
- User is free-only — never pitch hosted SaaS variants; self-hosted MIT is the answer.