#!/usr/bin/env python3
"""ETH 行情分析卡片 — 深色主题一图流"""
from PIL import Image, ImageDraw, ImageFont

W, H = 720, 760
BG      = "#101018"
CARD_BG = "#1b1b28"
UP      = "#e1594f"   # 涨红（加密惯例）
DOWN    = "#2e9e63"
TXT     = "#e8e8f0"
DIM     = "#9a9ab0"
ACC     = "#f0c94b"   # 强调黄

def font(sz, bold=False):
    path = "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"
    try:
        return ImageFont.truetype(path, sz)
    except Exception:
        return ImageFont.load_default()

def center_text(d, cx, y, text, f, fill):
    w = d.textbbox((0,0), text, font=f)[2]
    d.text((cx - w/2, y), text, fill=fill, font=f)

def right_text(d, x, y, text, f, fill):
    w = d.textbbox((0,0), text, font=f)[2]
    d.text((x - w, y), text, fill=fill, font=f)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

# 标题
center_text(d, W/2, 36, "ETH 多周期分析", font(30, True), TXT)
center_text(d, W/2, 78, "08-24 19:41 · 数据源 Binance", font(16), DIM)

# 现价卡
d.rounded_rectangle([40, 110, W-40, 210], 14, fill=CARD_BG)
center_text(d, W/2, 130, "现价", font(18), DIM)
center_text(d, W/2, 158, "$2502", font(52, True), UP)

# 趋势卡
d.rounded_rectangle([40, 228, W-40, 328], 14, fill=CARD_BG)
center_text(d, W/2, 246, "三周期趋势", font(18), DIM)
tfs = [("15m", "弱多", UP), ("1h", "弱多", UP), ("4h", "弱多", UP)]
x0 = 150
for name, val, col in tfs:
    center_text(d, x0, 276, name, font(20), DIM)
    center_text(d, x0, 302, val, font(26, True), col)
    x0 += 140

# 关键位卡
d.rounded_rectangle([40, 346, W-40, 470], 14, fill=CARD_BG)
center_text(d, W/2, 362, "关键位", font(18), DIM)
d.text((80, 394), "压力  2546  (4h 摆动高)", font=font(22), fill=DOWN)
d.text((80, 430), "支撑  2453 EMA20 / 2436 / 2424", font=font(22), fill=UP)

# 建议卡
d.rounded_rectangle([40, 488, W-40, 700], 14, fill=CARD_BG)
center_text(d, W/2, 504, "建议：做多（条件）", font(24, True), ACC)
lines = [
    "① 三周期全弱多头 + MACD 红柱扩张",
    "② 15m 放量 2.52x 突破 2484 阻力",
    "③ 触发：回踩 2436-2453 缩量企稳 + 15m 放量阳",
    "④ 止损 1xATR = 26",
]
y = 540
for l in lines:
    d.text((70, y), l, font=font(20), fill=TXT)
    y += 38

# 风险条
d.rounded_rectangle([40, 716, W-40, 744], 10, fill="#2a1f1f")
d.text((60, 722), "⚠ 4h 已超买 RSI71 + 4h 缩量 0.88x — 当下勿追高，等回踩", font=font(18), fill="#f0a0a0")

out = "D:/Hermes/workspace/eth_card.png"
img.save(out, quality=95)
print("saved:", out)