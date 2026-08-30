# -*- coding: utf-8 -*-
"""BlockBeats 快讯卡片生成器"""
import re, sys, argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

def wrap(text, font, max_w):
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur); cur = ""; continue
        t = cur + ch
        if font.getlength(t) > max_w and cur:
            lines.append(cur); cur = ch
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines

def render(item_id, title, content, link="", tstr=""):
    try:
        f12 = ImageFont.truetype(FONT, 12)
        f13 = ImageFont.truetype(FONT, 13)
        fb13 = ImageFont.truetype(FONT_BOLD, 13)
        f16 = ImageFont.truetype(FONT, 16)
        fb16 = ImageFont.truetype(FONT_BOLD, 16)
        fb28 = ImageFont.truetype(FONT_BOLD, 28)
    except:
        f12 = f13 = fb13 = f16 = fb16 = fb28 = ImageFont.load_default()

    W = 640
    PAD_L = 44
    PAD_R = 44
    BW = W - PAD_L - PAD_R

    body = content or ""
    m = re.match(r"^BlockBeats\s*消息[，,]\s*(.*)", body)
    if m:
        body = m.group(1)

    title_lines = wrap(title or "", fb28, BW)
    body_lines = wrap(body, f16, BW)

    H = (36 + 30 + len(title_lines) * 40 + 20 + len(body_lines) * 26 + 36 + 24)
    H = max(H, 200)

    img = Image.new("RGB", (W, H), (242, 238, 232))
    d = ImageDraw.Draw(img)

    y = 24
    d.rounded_rectangle([PAD_L, y, PAD_L + 28, y + 20], radius=3, fill=(200, 50, 40))
    d.text((PAD_L + 14, y + 10), "F", font=fb13, fill=(255, 255, 255), anchor="mm")
    if tstr:
        d.text((W - PAD_R, y + 10), tstr, font=f13, fill=(140, 135, 128), anchor="rm")
    y += 30

    for ln in title_lines:
        d.text((PAD_L, y), ln, font=fb28, fill=(30, 28, 25))
        y += 40
    y += 8
    d.rectangle([PAD_L, y, PAD_L + 40, y + 3], fill=(200, 80, 30))
    y += 16
    for ln in body_lines:
        d.text((PAD_L, y), ln, font=f16, fill=(45, 42, 38))
        y += 26
    y += 16
    d.text((PAD_L, y), "BlockBeats · 实时推送", font=f12, fill=(150, 145, 138))

    out = Path(f"/tmp/flash_{item_id}.png")
    img.save(out, "PNG", quality=95)
    return str(out)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", default="364318")
    ap.add_argument("--title", default="特朗普将用委内瑞拉石油填充美国战略储备")
    ap.add_argument("--content", default="BlockBeats 消息，8 月 30 日，美国总统特朗普：将用委内瑞拉石油填充美国国家战略储备。补充至满储水平的过程很快就会启动。")
    ap.add_argument("--time", default="22:14")
    args = ap.parse_args()
    render(args.id, args.title, args.content, tstr=args.time)
