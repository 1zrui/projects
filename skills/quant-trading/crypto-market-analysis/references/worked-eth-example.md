# Worked Example — ETH Multi-Timeframe Analysis (2026-08-27)

Concrete run done this session. Use as the canonical *output shape* for a "看看 ETH" request (analysis, not trade).

## Data source
Binance K-line via proxy `socks5h://127.0.0.1:10808`:
`https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval={15m,1h,4h}&limit={100,100,50}`
Plus 24h ticker: `.../ticker/24hr?symbol=ETHUSDT`

## Indicator set (compute, don't eyeball)
EMA(20/50/200), RSI14 (Wilder), MACD(12,26,9), Bollinger(20,2σ), ATR14, volume-ratio (last vol / 20-period mean), swing highs/lows (3-bar local extrema in last 20 bars).

## Trend classification rule
```
强多头: price>EMA20>EMA50>EMA200 and EMA20 slope>0
弱多头: price>EMA20 (not clearly bull-stacked)
震荡:   price within ±1% of EMA20 and EMA20 flat
弱空头: price<EMA20
强空头: price<EMA20<EMA50<EMA200
```

## Scoring (single-direction call)
```
trend score: 强多+2 弱多+1 震荡0 弱空-1 强空-2  (sum 15m/1h/4h)
RSI:   >80 +2空  >70 +1空  <30 +2多  <35 +1多
bias vs EMA20: >+7% +2空  >+5% +1空  <-5% +1多
vol_ratio: <0.7 +1空 (no-volume rally)  >1.5 +1多
15m vs 1h divergence: +1空
net = bull - bear
  net>=+2 → 做多(条件)   net<=-2 → 做空(条件)   else → 观望(偏多/偏空)
```
Always attach: 2-3 reasons citing actual computed numbers + trigger condition + stop (1×ATR or swing level). Never unconditional.

## ETH 2026-08-27 11:00 snapshot
- Price $2494.48, 24h +1.20%, range 2432.32–2515.38
- 15m/1h/4h all 强多头; RSI 52/59/64; MACD mixed (1h 金叉, 4h 死叉); vol_ratio 0.02–0.44x (极度缩量)
- Net +3 → 做多(条件): 回踩 2471–2487 缩量企稳+15m放量阳，或放量破 2515.38 追；止损 2471 下。
- Key risk flagged: 缩量下不追高，等放量确认。

## Deliverable format
markdown report with: 快照 / 三周期趋势表 / 支撑阻力(摆动点) / 证据对照(多空) / 关键位+失效 / 单一方向建议 / 非财务建议声明.
On qqbot channel send markdown directly; do NOT reuse NapCat-only send姿势 (copy-to-Downloads + file:///).
