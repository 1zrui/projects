"""crypto-trend-analyzer 参考实现 — 严谨分析引擎"""
from __future__ import annotations
import argparse, json, math, urllib.request
from datetime import datetime, timezone

BINANCE = "https://api.binance.com/api/v3"

def fetch_klines(symbol: str, interval: str, limit: int, proxy: str | None):
    url = f"{BINANCE}/klines?symbol={symbol}&interval={interval}&limit={limit}"
    # 走 SOCKS5 需用代理；urllib 不原生支持 socks，用 curl 回退或让用户装 pysocks
    # 简化：直接用 http 代理 127.0.0.1:10808 的 http 转发（xray 同端口支持 http）
    import subprocess, shlex
    if proxy and "socks" in proxy:
        http_proxy = proxy.replace("socks5h://", "http://").replace("socks5://", "http://")
        # xray 默认 10808 是 socks，http 需 10809 或走 socks 的 curl
        cmd = f'curl -s -x {proxy} "{url}"'
    else:
        cmd = f'curl -s "{url}"'
    out = subprocess.check_output(cmd, shell=True, timeout=15)
    return json.loads(out)

def ema(arr, n):
    k = 2/(n+1)
    e = arr[0]
    out = [e]
    for x in arr[1:]:
        e = x*k + e*(1-k)
        out.append(e)
    return out

def rsi_wilder(closes, n=14):
    if len(closes) <= n:
        return [None]*len(closes)
    gains = [max(closes[i]-closes[i-1], 0) for i in range(1, len(closes))]
    losses = [max(closes[i-1]-closes[i], 0) for i in range(1, len(closes))]
    ag = sum(gains[:n])/n
    al = sum(losses[:n])/n
    rsis = [None]*(n+1)
    for i in range(n, len(gains)):
        if i > n:
            ag = (ag*(n-1) + gains[i])/n
            al = (al*(n-1) + losses[i])/n
        rs = ag/(al+1e-9)
        rsi = 100 - 100/(1+rs)
        rsis.append(rsi)
    # pad to len(closes)
    while len(rsis) < len(closes):
        rsis.insert(0, None)
    return rsis[-len(closes):]

def atr(highs, lows, closes, n=14):
    trs = []
    for i in range(len(closes)):
        if i == 0:
            trs.append(highs[i]-lows[i])
        else:
            trs.append(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])))
    # Wilder
    a = sum(trs[:n])/n
    out = [None]*(n-1) + [a]
    for i in range(n, len(trs)):
        a = (a*(n-1)+trs[i])/n
        out.append(a)
    return out

def classify(closes, ema20, ema50, ema200=None):
    c, e20, e50 = closes[-1], ema20[-1], ema50[-1]
    e200 = ema200[-1] if ema200 and ema200[-1] is not None else None
    slope = ema20[-1] - ema20[-2] if len(ema20) >= 2 else 0
    if e200 is not None and c > e20 > e50 > e200 and slope > 0:
        return "强多头"
    if c > e20 and abs(c-e20)/e20 < 0.01 and abs(slope) < e20*0.001:
        return "震荡"
    if c > e20:
        return "弱多头"
    if e200 is not None and c < e20 < e50 < e200:
        return "强空头"
    if c < e20:
        return "弱空头"
    return "震荡"

def swing_levels(highs, lows, window=20):
    highs_win, lows_win = highs[-window:], lows[-window:]
    # 摆动高低点：3根中最高/最低
    swing_highs, swing_lows = [], []
    for i in range(1, window-1):
        if highs_win[i] == max(highs_win[i-1:i+2]):
            swing_highs.append(highs_win[i])
        if lows_win[i] == min(lows_win[i-1:i+2]):
            swing_lows.append(lows_win[i])
    swing_highs = sorted(set(swing_highs), reverse=True)[:3]
    swing_lows = sorted(set(swing_lows))[:3]
    return swing_highs, swing_lows

def analyze_symbol(symbol: str, proxy: str | None):
    tfs = [("15m", 100), ("1h", 100), ("4h", 50)]
    data = {}
    for tf, lim in tfs:
        kl = fetch_klines(symbol, tf, lim, proxy)
        closes = [float(k[4]) for k in kl]
        highs = [float(k[2]) for k in kl]
        lows = [float(k[3]) for k in kl]
        vols = [float(k[5]) for k in kl]
        e20, e50 = ema(closes, 20), ema(closes, 50)
        e200 = ema(closes, 200) if len(closes) >= 200 else [None]*len(closes)
        rsi = rsi_wilder(closes, 14)
        atr_vals = atr(highs, lows, closes, 14)
        trend = classify(closes, e20, e50, e200)
        sh, sl = swing_levels(highs, lows, 20)
        vol_ma = sum(vols[-20:])/20 if len(vols) >= 20 else sum(vols)/len(vols)
        vol_ratio = vols[-1]/vol_ma if vol_ma else 0
        data[tf] = dict(closes=closes, highs=highs, lows=lows, vols=vols,
                        e20=e20, e50=e50, e200=e200, rsi=rsi, atr=atr_vals,
                        trend=trend, swing_highs=sh, swing_lows=sl,
                        vol_ratio=vol_ratio, last_close=closes[-1])
    return data

def render(symbol: str, data: dict):
    # 取 1h 为主快照
    h1 = data["1h"]
    h4 = data["4h"]
    m15 = data["15m"]
    last = h1["last_close"]
    rsi1 = h1["rsi"][-1]
    e20_1 = h1["e20"][-1]
    bias = (last/e20_1-1)*100 if e20_1 else 0
    print(f"## {symbol} 多周期分析 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"\n### 快照")
    print(f"现价 ${last:.2f}  1h RSI {rsi1:.1f}  距EMA20 {bias:+.2f}%  量比 {h1['vol_ratio']:.2f}x  ATR {h1['atr'][-1]:.2f}")
    for tf in ("15m","1h","4h"):
        d = data[tf]
        print(f"- {tf}: 趋势={d['trend']}  RSI={d['rsi'][-1]:.1f}  量比={d['vol_ratio']:.2f}x  摆动高={d['swing_highs'][:2]} 摆动低={d['swing_lows'][:2]}")
    print(f"\n### 证据对照")
    print(f"| 维度 | 多头证据 | 空头证据 |")
    print(f"|------|----------|----------|")
    # 示例：按阈值自动填
    bull, bear = [], []
    if h1["trend"] in ("强多头","弱多头"): bull.append("1h多头")
    else: bear.append(f"1h {h1['trend']}")
    if rsi1 > 70: bear.append(f"RSI{rsi1:.0f}超买")
    elif rsi1 < 30: bull.append(f"RSI{rsi1:.0f}超卖")
    if abs(bias) > 7: bear.append(f"乖离{bias:.1f}%过大") if bias>0 else bull.append(f"乖离{bias:.1f}%")
    if h1["vol_ratio"] < 0.7: bear.append(f"缩量{h1['vol_ratio']:.2f}x")
    elif h1["vol_ratio"] > 1.5: bull.append(f"放量{h1['vol_ratio']:.2f}x")
    print(f"| 趋势+动能+量能 | {'; '.join(bull) or '—'} | {'; '.join(bear) or '—'} |")
    print(f"\n### 关键位与失效")
    print(f"- 阻力: {h1['swing_highs'][:2]} (1h摆动高) / {m15['swing_highs'][:1]} (15m)")
    print(f"- 支撑: {m15['swing_lows'][:1]} (15m) / {h1['swing_lows'][:1]} (1h) / EMA20 {e20_1:.2f}")
    print(f"- 失效: 跌破 {m15['swing_lows'][0]:.2f} 且15m放量阴线 → 回调确认；站稳 {h1['swing_highs'][0]:.2f} 且4h放量 → 突破延续")
    # Step 8 单一方向打分
    score_bull, score_bear = 0, 0
    # 趋势分
    trend_score = {"强多头":2,"弱多头":1,"震荡":0,"弱空头":-1,"强空头":-2}
    s = trend_score.get(m15['trend'],0)+trend_score.get(h1['trend'],0)+trend_score.get(h4['trend'],0)
    if s>0: score_bull+=s
    elif s<0: score_bear+=-s
    # RSI
    if rsi1 is not None:
        if rsi1>80: score_bear+=2
        elif rsi1>70: score_bear+=1
        elif rsi1<30: score_bull+=2
        elif rsi1<35: score_bull+=1
    # 乖离
    if bias>7: score_bear+=2
    elif bias>5: score_bear+=1
    elif bias<-5: score_bull+=1
    # 量比（无量上涨不确认，算空）
    if h1['vol_ratio']<0.7: score_bear+=1
    elif h1['vol_ratio']>1.5: score_bull+=1
    # 背离
    if m15['trend']!=h1['trend'] and m15['trend']=="震荡" and h1['trend'] in ("弱多头","强多头"):
        score_bear+=1
    net = score_bull - score_bear
    atr1 = h1['atr'][-1]
    sup15 = m15['swing_lows'][0] if m15['swing_lows'] else e20_1
    res1 = h1['swing_highs'][0] if h1['swing_highs'] else last*1.02
    # 理由
    reasons_bull, reasons_bear = [], []
    if h1['trend'] in ("强多头","弱多头"): reasons_bull.append(f"1h{ h1['trend'] }")
    if h4['trend'] in ("强多头","弱多头"): reasons_bull.append(f"4h{ h4['trend'] }")
    if rsi1 and rsi1<35: reasons_bull.append(f"RSI{rsi1:.0f}超卖")
    if rsi1 and rsi1>70: reasons_bear.append(f"RSI{rsi1:.0f}超买")
    if abs(bias)>5: 
        if bias>0: reasons_bear.append(f"乖离{bias:+.1f}%过大")
        else: reasons_bull.append(f"乖离{bias:+.1f}%")
    if h1['vol_ratio']<0.7: reasons_bear.append(f"1h缩量{h1['vol_ratio']:.2f}x滞涨")
    elif h1['vol_ratio']>1.5: reasons_bull.append(f"放量{h1['vol_ratio']:.2f}x")
    if m15['trend']=="震荡": reasons_bear.append("15m转震荡")
    if net >= 2:
        rb = "、".join(reasons_bull[:3]) or "多头占优"
        print(f"\n### 建议：做多（条件）— 理由：{rb}。触发：回踩{sup15:.2f}缩量企稳且15m放量阳收回，止损1xATR({atr1:.2f})。")
    elif net <= -2:
        rb = "、".join(reasons_bear[:3]) or "空头占优"
        print(f"\n### 建议：做空（条件）— 理由：{rb}。触发：跌破{sup15:.2f}且15m放量阴确认，止损{res1:.2f}上方。")
    else:
        bias_dir = "偏空" if net<0 else ("偏多" if net>0 else "")
        reasons = reasons_bear if net<=0 else reasons_bull
        rb = "、".join(reasons[:3]) or ("多空均势" if net==0 else "")
        print(f"\n### 建议：观望{bias_dir} — 理由：{rb}。触发：跌破{sup15:.2f}放量阴才考虑短空；回踩企稳放量阳才考虑做多。止损参考1xATR({atr1:.2f})。")
    print(f"\n> 非财务建议。止损参考 1xATR: {atr1:.2f}。不构成开仓建议，满足触发才考虑。")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="ETHUSDT")
    ap.add_argument("--proxy", default="socks5h://127.0.0.1:10808")
    args = ap.parse_args()
    data = analyze_symbol(args.symbol, args.proxy)
    render(args.symbol, data)
