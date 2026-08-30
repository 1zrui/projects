#!/usr/bin/env python3
"""表格转图片 —— 把 Markdown 表格渲染成高清图片，QQ 友好"""

import sys, json, textwrap
from PIL import Image, ImageDraw, ImageFont

# ── 配色（深色主题，适合 QQ 聊天背景） ──────────────────────────
BG_COLOR     = "#1e1e2e"     # 背景
HEADER_BG    = "#2a2a3e"     # 表头背景
ROW_EVEN_BG  = "#252538"     # 偶数行背景
ROW_ODD_BG   = "#1e1e2e"     # 奇数行背景
TEXT_COLOR   = "#cdd6f4"     # 文字颜色
HEADER_COLOR = "#ffffff"     # 表头文字颜色
BORDER_COLOR = "#45475a"     # 边框颜色
FONT_PATH    = ""            # 留空自动找中文字体

# ── 字体配置 ────────────────────────────────────────────────────
FONT_SIZE = 16
HEADER_FONT_SIZE = 17
PADDING  = 12   # 单元格内边距
MARGIN   = 20   # 图片外边距
COL_GAP  = 8    # 列间距

def find_chinese_font():
    """自动搜索系统上的中文字体"""
    import os
    candidates = [
        # Linux
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        # macOS
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        # Windows
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # 让 matplotlib 找
    import matplotlib.font_manager as fm
    for f in fm.fontManager.ttflist:
        if 'CJK' in f.name or 'Noto' in f.name or 'WenQuanYi' in f.name or 'Heiti' in f.name or 'Microsoft YaHei' in f.name:
            return f.fname
    return None

def parse_markdown_table(text):
    """解析 Markdown 表格文本，返回 [headers], [rows]"""
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
    if not lines:
        return [], []
    # 跳过分隔行 (|---|---|)
    data_lines = [l for l in lines if not l.replace('|', '').replace('-', '').replace(':', '').strip() == '']
    if not data_lines:
        return [], []
    headers = [c.strip() for c in data_lines[0].strip('|').split('|')]
    rows = []
    for line in data_lines[1:]:
        cells = [c.strip() for c in line.strip('|').split('|')]
        # 补齐长度
        while len(cells) < len(headers):
            cells.append('')
        rows.append(cells[:len(headers)])
    return headers, rows

def calc_col_widths(draw, headers, rows, font, header_font):
    """计算每列所需宽度"""
    n_cols = len(headers)
    widths = [0] * n_cols
    for i, h in enumerate(headers):
        w = header_font.getbbox(h)[2] + PADDING * 2
        widths[i] = max(widths[i], w)
    for row in rows:
        for i, cell in enumerate(row):
            if i < n_cols:
                w = 0
                for line in cell.split('\n'):
                    lw = font.getbbox(line)[2] + PADDING * 2
                    w = max(w, lw)
                widths[i] = max(widths[i], w)
    return widths

def render_table(headers, rows, output_path="table.png"):
    """渲染表格为图片"""
    font_path = find_chinese_font()
    
    font = ImageFont.truetype(font_path, FONT_SIZE) if font_path else ImageFont.load_default()
    header_font = ImageFont.truetype(font_path, HEADER_FONT_SIZE) if font_path else ImageFont.load_default()

    # 用 draw 计算文字尺寸
    dummy_img = Image.new('RGB', (1, 1))
    draw = ImageDraw.Draw(dummy_img)

    col_widths = calc_col_widths(draw, headers, rows, font, header_font)
    n_cols = len(headers)
    
    # 行高
    row_height = FONT_SIZE + PADDING * 2 + 4
    header_row_height = HEADER_FONT_SIZE + PADDING * 2 + 4
    total_rows = 1 + len(rows)  # 表头 + 数据行

    # 图片尺寸
    total_width = sum(col_widths) + COL_GAP * (n_cols - 1) + MARGIN * 2
    total_height = header_row_height + row_height * len(rows) + MARGIN * 2

    img = Image.new('RGB', (int(total_width), int(total_height)), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # ── 绘制表格 ──
    x_positions = [MARGIN]
    for w in col_widths:
        x_positions.append(x_positions[-1] + w + COL_GAP)
    
    y = MARGIN

    # 表头
    for i, h in enumerate(headers):
        x1 = x_positions[i]
        x2 = x_positions[i+1]
        draw.rectangle([x1, y, x2, y + header_row_height], fill=HEADER_BG, outline=BORDER_COLOR, width=1)
        draw.text((x1 + PADDING, y + PADDING), h, fill=HEADER_COLOR, font=header_font)
    
    y += header_row_height

    # 数据行
    for ri, row in enumerate(rows):
        bg = ROW_EVEN_BG if ri % 2 == 0 else ROW_ODD_BG
        for i, cell in enumerate(row):
            x1 = x_positions[i]
            x2 = x_positions[i+1]
            draw.rectangle([x1, y, x2, y + row_height], fill=bg, outline=BORDER_COLOR, width=1)
            # 如果单元格有多行，绘制第一行（简化处理）
            first_line = cell.split('\n')[0] if cell else ''
            draw.text((x1 + PADDING, y + PADDING), first_line, fill=TEXT_COLOR, font=font)
        y += row_height

    img.save(output_path, quality=95)
    return output_path

def main():
    if len(sys.argv) < 2:
        # 从 stdin 读取
        text = sys.stdin.read().strip()
    else:
        # 从文件或直接参数读取
        if sys.argv[1] == '-f':
            with open(sys.argv[2], 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            text = ' '.join(sys.argv[1:])
    
    if not text:
        print("Usage: python3 table2img.py <markdown_table_text>")
        print("   or: cat table.md | python3 table2img.py")
        print("   or: python3 table2img.py -f input.md")
        sys.exit(1)

    headers, rows = parse_markdown_table(text)
    if not headers:
        print("Error: 无法解析表格，请确保是 Markdown 表格格式")
        sys.exit(1)

    path = render_table(headers, rows)
    print(f"✅ 表格已生成: {path}")

if __name__ == '__main__':
    main()