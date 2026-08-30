# Crypto Trend & Market Analysis

## Core workflow — 三步全做，缺一不可

### 1. Live price first
```bash
curl -s "https://api.coingecko.com/api/v3/simple/price?ids=ethereum,bitcoin&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true&include_market_cap=true"
```

### 2. Catalyst search
web_search `crypto <coin> news <date>`
- ETF flows（资金流向）
- Whale activity（鲸鱼动向）
- Liquidation cascades（清算潮）
- Policy bills（政策法案）
- Fear&Greed index

### 3. Technical analysis（TradingView MCP）
- `coin_analysis(symbol, exchange, timeframe)` — 单周期深度
- `multi_timeframe_analysis(symbol, exchange)` — 多周期对齐
- `bitcoin_market_pulse()` — BTC宏观背景

## 分析输出模板

```
## [币种] 合约分析

### 📊 实时价格
- [币种]: $价格 (涨跌幅 / 24h)
- BTC: $价格 (涨跌幅)
- 市值/主导率

### 📰 催化剂
1. [事件1] — 影响
2. [事件2] — 影响

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
- 短线（1-4h）
- 中线（日线）
- 风险提示
- 结论
```

## 工具链
1. CoinGecko → 实时价格（免费无key）
2. Web Search → 催化剂新闻
3. TradingView MCP → 技术分析（37工具，免费无账号）

## Pitfalls
- 催化剂搜索绝不能跳过
- TradingView是现货价格，合约/永续用ccxt
- bitcoin_market_pulse分析任何币前先调一次
