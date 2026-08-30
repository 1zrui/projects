---
name: crypto-trend-analyzer
description: Use when analyzing cryptocurrency price trends — multi-timeframe technical analysis with strict evidence-based discipline. Fetches Binance K-lines, computes EMA/RSI/MACD/Bollinger/ATR, classifies trend by rule, identifies S/R from swings, checks volume confirmation, and outputs a structured report with bull/bear evidence, key levels, invalidation, and ONE scored directional call (long/short/hold-with-bias + reasons + trigger/stop) — no unconditional calls, no price targets without conditions.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [crypto, trend-analysis, technical-analysis, binance, quant]
    related_skills: [crypto-quant-backtesting, quant-trading-platform]
---

# Crypto Trend Analyzer — 严谨走势分析

## Overview

只做**分析**，不做**猜测**。输入币种（BTC/ETH/SOL…）→ 拉多周期 K 线 → 按固定规则算指标 → 分类趋势 → 找支撑阻力 → 验量能 → 输出证据对照表 + 关键位 + 失效条件。所有结论必须有数据一句一对应，禁止无依据的"看涨/看跌"结论。

核心纪律：**无证据不下结论，有结论必给失效位。**

## When to Use

- 用户说"分析XX" "ETH走势怎么样" "看看BTC" "预测后面会涨还是跌"（此时转为严谨分析）
- 需要多周期（15m/1h/4h）技术面拆解
- 需要支撑/阻力/乖离/超买超卖的量化判断
- 量化回测之外的**盘面研判**场景

**Don't use for:**
- 实盘下单/开仓（用 quant-trader 回测链路）
- 链上深度研报（那是 crypto-token-research 的活）
- 纯新闻/情绪面分析（无 K 线不分析）

## Workflow — 7 步严谨分析

### Step 1: 拉数据（做完成标准：三周期齐全且新鲜）

```bash
# 经本机 xray SOCKS5 127.0.0.1:10808 走 Binance
curl -s -x socks5h://127.0.0.1:10808 \
  "https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=1h&limit=100"
# 三档必拉：15m(100根) / 1h(100根) / 4h(50根)
# 校验：最后收盘时间距 now < 2*周期，否则标注"数据滞后"
```

`quant-trader/data/store.py` 的 DuckDB 可作备用（已存 23000+ 根）。

### Step 2: 算指标（做完成标准：6 项齐全）

| 指标 | 参数 | 作用 | 阈值 |
|------|------|------|------|
| EMA | 20/50/200 | 趋势方向+乖离 | 价格距 EMA20 >7% 记"乖离过大" |
| RSI14 | Wilder | 超买超卖 | >70超买 >80极度 <30超卖 |
| MACD | 12,26,9 | 动能 | 只看金叉/死叉 + 柱状收缩/扩张 |
| Bollinger | 20,2σ | 波动扩张/Mean Reversion | 触上轨+缩口=滞涨信号 |
| ATR14 | — | 设止损位参考 | 支撑 = 摆动低点 - 1xATR |
| 量比 | 最新量/20周期均量 | 确认 | >1.5放量 <0.7缩量 |

RSI 公式严用 Wilder 平滑，不用简单平均。

### Step 3: 趋势分类（规则化，禁止主观）

```
强多头: 价格>EMA20>EMA50>EMA200 且 EMA20斜率>0
弱多头: 价格>EMA20 但 EMA20/50缠绕
震荡:   价格在 EMA20±1% 内且 EMA20走平
弱空头: 价格<EMA20 但未破 EMA50
强空头: 价格<EMA20<EMA50<EMA200
```

必须同时给出 15m/1h/4h 三档分类，不一致时标注"周期背离"。

### Step 4: 支撑阻力（只认摆动点，不画主观线）

- 摆动高点 = 连续 3 根中最高那根
- 摆动低点 = 连续 3 根中最低那根
- 关键位取最近 20 根内的摆动点，按有效性排序（被测试次数越多越强）
- 不编造整数关口，整数关口只作"心理位"备注

### Step 5: 量价校验

- 放量上涨 = 真突破；缩量上涨 = 假突破/滞涨
- 高位放量上影 = 抛压
- 最新量 vs 20 周期均量，给具体倍数，不说"放量"空话

### Step 6: 综合 — 证据对照表（必输出）

```markdown
| 维度 | 多头证据 | 空头证据 |
|------|---------|---------|
| 趋势 | 1h EMA多头排列 | 15m 已跌破EMA20 |
| 动能 | MACD 金叉 | RSI 86 极度超买 |
| 量能 | 24h量 82万 | 最新量比 0.5x 缩量 |
| 结构 | 突破 2100 | 2333 前高强阻 |
```

证据数多的一方≠结论，只说"当前多/空证据各 N 条"。

### Step 7: 关键位 + 失效条件（必输出）

```
上方阻力: 2333 (4h摆动高，强) / 2274 (15m上影)
下方支撑: 2250 (15m密集) / 2200 (1h回调首位) / 2110 (EMA20)
失效位:   跌破 2250 且 15m 放量阴线 → 短线回调确认
        站稳 2333 且 4h 放量 → 突破延续
```

每条关键位必注来源周期+强度，失效位必给"价格+量能"双条件。

### Step 8: 单一方向建议（必输出 — 只给一个方向 + 2-3条理由）

根据 Step 6 证据做**打分**，只输出最占优的那个方向，禁止三行都摆：

```
打分：
  趋势：强多头+2 / 弱多头+1 / 震荡0 / 弱空头-1 / 强空头-2 （15m/1h/4h 分别计分后求和，>0偏多 <0偏空）
  RSI：>80 空+2 / >70 空+1 / <30 多+2 / <35 多+1
  乖离：距EMA20>+5% 空+1 / >+7% 再+1；<-5% 多+1
  量比：<0.7 空+1（无量上涨不确认）/ >1.5 多+1
  背离：15m与1h趋势不一致 空+1

净分 = 多分 - 空分
  净分 >= +2 → 建议做多（条件）
  净分 <= -2 → 建议做空（条件）
  否则       → 建议观望（说明偏多/偏空）
```

输出格式（单行方向 + 理由，理由必引 2 项已算指标）：

```
建议：观望（偏空）— 理由：① RSI85超买 ② 乖离+6.4%过大 ③ 1h量比0.17x缩量滞涨。触发：跌破2241且15m放量阴才考虑短空；回踩企稳且放量阳才考虑做多。
建议：做多（条件）— 理由：① 1h强多头 ② RSI38超卖 ③ 放量1.8x确认。触发：回踩2250缩量企稳且15m放量阳收回，止损1xATR。
```

纪律：
- 只能给一个方向（做多 / 做空 / 观望），观望必须标偏多/偏空
- 理由 2-3 条，每条必是 Step 2-5 已算的数（RSI/乖离/量比/趋势）
- 必须带触发条件与止损（1xATR 或摆动位），禁止无条件"建议做多"

## QQ / 聊天交付铁律（大哥 2026-08-24 纠正）

**第一步：先确认用户在哪个通道，再决定交付格式。** 这是 2026-08-27 踩坑教训——把 NapCat 的 `file:///`+PNG 流程套到 qqbot（官方机器人）通道上，用户收不到图还 confused。

| 通道 | 识别特征 | markdown 渲染 | 身份标识 | 正确交付方式 |
|------|---------|--------------|---------|------------|
| **NapCat**（OneBot，桌面端登录 bot） | self_id 是数字 QQ（如 779139587），私聊/群聊走 OneBot 11 | ❌ 不渲染，文本堆过去=乱码墙 | 真实 QQ 号（2415317075 等） | 渲染 PNG 卡片 → 拷 `C:/Users/Administrator/Downloads/` → `send_private_msg` + `file:///`，图后跟 ≤3 行纯文本结论 |
| **qqbot**（官方机器人，app_id 接入） | home_channel 是 openid（如 `ADA809A2441B9620CB07A76D331917DF`），非数字 QQ | ✅ 原生渲染 markdown | openid（**还原不出明文 QQ 号**，群内是 `member_openid` 哈希） | **直接发 markdown 文本报告即可**，不用转图、不用 `file:///`、不用 `MEDIA:` |

判断信号：会话 Source 标 `qqbot` / 对话 ID 是 openid 格式 → 走 qqbot 列；标 `napcat` / 数字 QQ 号 → 走 NapCat 列。拿不准就先看会话元数据的 `Source` 与 `User ID` 字段，别凭记忆默认 NapCat。

**NapCat 专用铁律**（qqbot 不适用，跳过）：
- 禁止把整份 markdown 报告当文本发 NapCat（大哥原话：「你发这一堆文本，根本看不懂，乱的很」）
- `MEDIA:` 标记在 NapCat 下发图不可靠（2026-08-24 实测发不出去），别再用
- 发图只走 `C:/Users/Administrator/Downloads/` + `file:///`，**别发 D 盘/桌面路径**

### NapCat 通道交付流程（qqbot 通道直接发 markdown，不用下面这套）
1. 分析引擎跑完拿数据（`references/analyze.py`）
2. 渲染卡片：推荐 `scripts/eth_live_card.py`（本技能自带，**实时拉 Binance 数据 + 自动打分 + 渲染 PNG**，跑一次出图直接发；`D:/Hermes/scripts/eth_card.py` 是静态模板，改币种名即可复用）—— 任何币种改脚本里的 `ETHUSDT` 和标题即可复用
3. 拷 `C:/Users/Administrator/Downloads/` → NapCat `send_private_msg` + `file:///` 发送（完整姿势见 `napcat` 技能）
4. 图后跟 ≤3 行纯文本结论（价格+方向+触发+止损），别复述整表

## Report Template

```markdown
## {SYMBOL} 多周期分析 — {YYYY-MM-DD HH:mm} (UTC+8)

### 快照
现价 $X  24h +Y%  高$H 低$L  量 V

### 1h / 4h / 15m 三档
- 1h: 趋势=__  RSI=__  距EMA20=__%  量比=__x
- 4h: ...
- 15m: ...

### 趋势分类
...

### 支撑阻力
...

### 证据对照
| 维度 | 多头 | 空头 |

### 关键位与失效
...

### 条件化建议（单一方向 + 理由，必引2指标）
> 建议：观望（偏空）— 理由：① ... ② ... ③ ...  触发：... 止损：1xATR=...

### 结论（只说概率结构，不预言点位）
> 短线 回调/震荡概率 > 爆拉延续，依据：超买+乖离+缩量滞涨...
> 中线 需看 4h 是否站稳 2333，否则仍是反弹非反转...

> 非财务建议。止损参考 ATR: __。不构成开仓建议，满足触发条件才考虑。
```

## 准确性验证（被问"数据准吗"必走）

`ticker/price` vs K线收盘价、24h高低点、15m与1h自洽三步交叉验证，详见 `references/data-accuracy-verification.md`（含 2026-08-20 实测案例+时效性陷阱）。

## Common Pitfalls

1. **用预测替代分析** — 禁止"明天涨到XX"，只能说"若站稳XX则...否则..."
2. **单周期下结论** — 必须 15m+1h+4h 三档，单看 1h 等于盲人摸象
3. **RSI 算错** — 必须 Wilder 平滑，简单平均会虚高/虚低 5-10 点
4. **支撑阻力拍脑袋** — 必须摆动点回溯，不许画整数关口当"强支撑"
5. **量能空话** — 必须给量比倍数，"放量"二字无意义
6. **幸存者偏差** — 只看 24h 暴涨不看 7 天位置，误把反弹当趋势
7. **代理直连失败** — Binance 必须走 `socks5h://127.0.0.1:10808`，直连超时
8. **数据滞后不标注** — K 线时间戳要校验，滞后 10 分钟以上必须声明
9. **建议摆三选一** — 用户明确要求只给一个方向+理由（观望必标偏多/偏空），禁止做多/做空/观望三行平铺。历史曾被纠正"不是三行，是只给一个方向加上理由"（2026-08-20）
10. **把建议当成开仓指令读** — 每条建议都是"若触发则..."的条件单，未满足触发价/量能前就是观望；止损用 1xATR 或摆动位，不给无条件入场点
11. **通道搞混导致交付失败** — 2026-08-27 把 NapCat 的 `file:///`+PNG 流程套到 qqbot（官方机器人）通道，用户收不到图。发报告前**先认通道**：会话 Source=`qqbot`/对话ID是openid → 直接发 markdown 文本；Source=`napcat`/数字QQ → 走 PNG+`file:///` 发图。详见上方「QQ / 聊天交付铁律」通道对照表

## Verification Checklist

- [ ] 三周期 K 线已拉且时间戳新鲜（<2*周期）
- [ ] 6 指标（EMA/RSI/MACD/BB/ATR/量比）数值齐全且公式正确
- [ ] 趋势分类按规则表判定，非主观
- [ ] 支撑阻力来自摆动点，有周期+强度标注
- [ ] 证据对照表多/空各至少 2 条
- [ ] 关键位+失效位双条件齐全
- [ ] 单一方向建议（做多/做空/观望偏XX）+2-3条理由（引指标）+触发与止损
- [ ] 观望必标偏多/偏空，禁止无条件喊单
- [ ] 全文无"必涨/必跌/看到XX"等预言句式
- [ ] 末尾有"非财务建议"与 ATR 止损参考

## One-Shot Recipe — 分析 ETH

```bash
# 1. 拉三周期
for tf in 15m 1h 4h; do echo "==$tf=="; curl -s -x socks5h://127.0.0.1:10808 "https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=$tf&limit=100" | python -c "import json,sys;d=json.load(sys.stdin);print(d[-1])"; done
# 2. 跑 scripts/analyze.py （见 references/analyze.py）
python scripts/analyze.py --symbol ETHUSDT --proxy socks5h://127.0.0.1:10808
```
