#!/usr/bin/env python3
"""ETH 行情分析卡片 — 实时拉数据 + 渲染 720x760 深色一图流。
任意币种复用：改 SYMBOL、标题、配色即可。输出 D:/Hermes/workspace/eth_card.png
发 QQ 姿势见 napcat 技能：拷 Downloads → send_private_msg + file:///。
"""
from __future__ import annotations
import json, subprocess
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

BINANCE = "https://api.binance.com/api/v3"
PROXY = "socks5h://127.0.0.1:10808"   # 本机 xray，Binance 必须走代理
W, H = 720, 760
BG      = "#101018"
CARD_BG = "#1b1b28"
UP      = "#e1594f"   # 加密行情惯例涨红
DOWN    = "#2e9e63"
TXT     = "#e8e8f0"
DIM     = "#9a9ab0"
ACC     = "#f0c94b"

def font(sz, bold=False):
    p = "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"
    try: return ImageFont.truetype(p, sz)
    except: return ImageFont.load_default()

def center(d, cx, y, t, f, fill):
    w = d.textbbox((0,0), t, font=f)[2]
    d.text((cx-w/2, y), t, fill=fill, font=f)

def fetch(interval, limit=100):
    url = f"{BINANCE}/klines?symbol=ETHUSDT&interval={interval}&limit={limit}"
    out = subprocess.check_output(f'curl -s -m15 -x {PROXY} "{url}"', shell=True, timeout=20)
    return json.loads(out)

def ema(arr, n):
    k = 2/(n+1); e = arr[0]; out = [e]
    for x in arr[1:]: e = x*k + e*(1-k); out.append(e)
    return out

def rsi_wilder(closes, n=14):
    if len(closes) <= n: return [None]*len(closes)
    gains = [max(closes[i]-closes[i-1],0) for i in range(1,len(closes))]
    losses = [max(closes[i-1]-closes[i],0) for i in range(1,len(closes))]
    ag = sum(gains[:n])/n; al = sum(losses[:n])/n
    rsis = [None]*(n+1)
    for i in range(n, len(gains)):
        if i > n: ag = (ag*(n-1)+gains[i])/n; al = (al*(n-1)+losses[i])/n
        rs = ag/(al+1e-9); rsis.append(100-100/(1+rs))
    while len(rsis) < len(closes): rsis.insert(0, None)
    return rsis[-len(closes):]

def atr(highs, lows, closes, n=14):
    trs = [highs[0]-lows[0]]
    for i in range(1,len(closes)):
        trs.append(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])))
    a = sum(trs[:n])/n; out = [None]*(n-1)+[a]
    for i in range(n, len(trs)): a = (a*(n-1)+trs[i])/n; out.append(a)
    return out

def classify(closes, e20, e50):
    c, e20v, e50v = closes[-1], e20[-1], e50[-1]
    slope = e20[-1]-e20[-2] if len(e20)>=2 else 0
    if c > e20v > e50v and slope > 0: return "强多头"
    if c > e20v and abs(c-e20v)/e20v < 0.01 and abs(slope) < e20v*0.001: return "震荡"
    if c > e20v: return "弱多头"
    if c < e20v < e50v: return "强空头"
    if c < e20v: return "弱空头"
    return "震荡"

def swing_levels(highs, lows, window=20):
    hw, lw = highs[-window:], lows[-window:]
    sh, sl = [], []
    for i in range(1, window-1):
        if hw[i] == max(hw[i-1:i+2]): sh.append(hw[i])
        if lw[i] == min(lw[i-1:i+2]): sl.append(lw[i])
    return sorted(set(sh), reverse=True)[:3], sorted(set(sl))[:3]

# ── 拉数据 ──
data = {}
for tf, lim in [("15m",100),("1h",100),("4h",50)]:
    kl = fetch(tf, lim)
    closes = [float(k[4]) for k in kl]
    highs  = [float(k[2]) for k in kl]
    lows   = [float(k[3]) for k in kl]
    vols   = [float(k[5]) for k in kl]
    e20, e50 = ema(closes,20), ema(closes,50)
    rsi = rsi_wilder(closes,14)
    atr_vals = atr(highs, lows, closes, 14)
    trend = classify(closes, e20, e50)
    sh, sl = swing_levels(highs, lows, 20)
    vol_ma = sum(vols[-20:])/20
    vol_ratio = vols[-1]/vol_ma if vol_ma else 0
    data[tf] = dict(closes=closes, e20=e20, rsi=rsi, atr=atr_vals,
                    trend=trend, swing_highs=sh, swing_lows=sl,
                    vol_ratio=vol_ratio, last_close=closes[-1])

h1, h4, m15 = data["1h"], data["4h"], data["15m"]
last = h1["last_close"]
rsi1, rsi4 = h1["rsi"][-1], h4["rsi"][-1]
e20_1 = h1["e20"][-1]
bias = (last/e20_1-1)*100 if e20_1 else 0
vr1, vr4, vr15 = h1["vol_ratio"], h4["vol_ratio"], m15["vol_ratio"]

# 打分（净分>=+2 做多 / <=-2 做空 / 否则观望偏XX）
sb, so = 0, 0
ts = {"强多头":2,"弱多头":1,"震荡":0,"弱空头":-1,"强空头":-2}
s = ts.get(m15['trend'],0)+ts.get(h1['trend'],0)+ts.get(h4['trend'],0)
if s > 0:
    sb += s
else:
    so += -s
if rsi1 and rsi1>80: so+=2
elif rsi1 and rsi1>70: so+=1
elif rsi1 and rsi1<30: sb+=2
elif rsi1 and rsi1<35: sb+=1
if bias>7: so+=2
elif bias>5: so+=1
if vr1<0.7: so+=1
elif vr1>1.5: sb+=1
net = sb-so
atr1 = h1['atr'][-1]
sup15 = m15['swing_lows'][0] if m15['swing_lows'] else e20_1
res1 = h1['swing_highs'][0] if h1['swing_highs'] else last*1.02

# ── 渲染 ──
img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

center(d, W/2, 36, "ETH 多周期分析", font(30,True), TXT)
center(d, W/2, 78, f"{datetime.now().strftime('%m-%d %H:%M')} · Binance", font(16), DIM)

d.rounded_rectangle([40,110,W-40,210], 14, fill=CARD_BG)
center(d, W/2, 130, "现价", font(18), DIM)
center(d, W/2, 158, f"${last:.2f}", font(52,True), UP)

d.rounded_rectangle([40,228,W-40,328], 14, fill=CARD_BG)
center(d, W/2, 246, "三周期趋势", font(18), DIM)
x0 = 150
for name, val, col in [("15m", m15['trend'], UP), ("1h", h1['trend'], UP), ("4h", h4['trend'], UP)]:
    center(d, x0, 276, name, font(20), DIM)
    center(d, x0, 302, val, font(26,True), col)
    x0 += 140

d.rounded_rectangle([40,346,W-40,470], 14, fill=CARD_BG)
center(d, W/2, 362, "关键位", font(18), DIM)
d.text((80, 394), f"压力  {res1:.2f}  (1h 摆动高)", font=font(22), fill=DOWN)
d.text((80, 430), f"支撑  {sup15:.2f}  (15m)  /  {e20_1:.2f}  (EMA20)", font=font(22), fill=UP)

d.rounded_rectangle([40,488,W-40,700], 14, fill=CARD_BG)
if net >= 2:
    direction = "做多（条件）"
    lines = [f"① 趋势: {m15['trend']}/{h1['trend']}/{h4['trend']}",
             f"② RSI 1h={rsi1:.0f}  4h={rsi4:.0f}",
             f"③ 触发: 回踩 {sup15:.2f} 缩量企稳 + 15m 放量阳",
             f"④ 止损 1xATR = {atr1:.2f}"]
elif net <= -2:
    direction = "做空（条件）"
    lines = [f"① 趋势: {m15['trend']}/{h1['trend']}/{h4['trend']}",
             f"② RSI 1h={rsi1:.0f}  4h={rsi4:.0f}",
             f"③ 触发: 跌破 {sup15:.2f} + 15m 放量阴确认",
             f"④ 止损 {res1:.2f} 上方"]
else:
    bias_dir = "偏空" if net<0 else ("偏多" if net>0 else "")
    direction = f"观望{bias_dir}"
    lines = [f"① 趋势: {m15['trend']}/{h1['trend']}/{h4['trend']}",
             f"② RSI 1h={rsi1:.0f}  4h={rsi4:.0f}",
             f"③ 触发: 跌破 {sup15:.2f} 放量阴才短空 / 企稳放量阳再做多",
             f"④ 止损参考 1xATR = {atr1:.2f}"]
center(d, W/2, 504, direction, font(24,True), ACC)
y = 540
for l in lines:
    d.text((70, y), l, font=font(20), fill=TXT)
    y += 38

warn_text = f"RSI 1h={rsi1:.0f}  4h={rsi4:.0f}  量比 15m={vr15:.2f}x  1h={vr1:.2f}x  4h={vr4:.2f}x"
d.rounded_rectangle([40,716,W-40,744], 10, fill="#2a1f1f")
d.text((50, 720), warn_text, font=font(18), fill="#f0a0a0")

out = "D:/Hermes/workspace/eth_card.png"
img.save(out, quality=95)
print(f"saved: {out}")
print(f"现价 ${last:.2f}  1h RSI {rsi1:.1f}  4h RSI {rsi4:.1f}  偏{bias:+.2f}%  量比 15m={vr15:.2f}x 1h={vr1:.2f}x")
print(f"趋势 15m={m15['trend']} 1h={h1['trend']} 4h={h4['trend']}  净分={net:+d}  方向={direction}")