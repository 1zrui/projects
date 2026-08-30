#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
opencode_go_rank.py — 抓取 opencode.ai/docs/go 的 5小时请求数排行，按 requests per 5 hour 倒序排榜
- 每天 cron 调用一次，直接打印榜单即为投递内容
- 会在 D:/Hermes/cron/opencode_go_rank_state.json 存上一期数据，用于显示名次变动 / 数值变动
- 无参数时 prints 中文榜单；可被 cron no_agent=true 直接调用
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

try:
    import requests
except ImportError:
    print("缺少 requests，请 pip install requests", file=sys.stderr)
    sys.exit(3)

URL = "https://opencode.ai/docs/go"
STATE_PATH = Path("D:/Hermes/cron/opencode_go_rank_state.json")
# 也保留一份历史快照
HISTORY_DIR = Path("D:/Hermes/cron/opencode_go_history")
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

BEIJING = timezone(timedelta(hours=8))

def fetch_md() -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    r = requests.get(URL, headers=headers, timeout=20)
    r.raise_for_status()
    return r.text

def parse_table(html: str):
    """
    页面是 Astro/Starlight 渲染的 HTML，榜单是 <table><thead><tr><th>Model</th><th>requests per 5 hour</th>...
    直接用正则抓该表格的 <tr><td> 行。
    """
    # 1) 优先：定位包含 "requests per 5 hour" 的 table 块
    tables = re.findall(r"<table.*?>.*?</table>", html, re.S | re.I)
    target = None
    for t in tables:
        if re.search(r"requests per 5 hour", t, re.I):
            # 确保有 Model 表头且是 4 列（Model / 5h / week / month），避免命中价格表
            if re.search(r"<th[^>]*>\s*Model\s*</th>", t, re.I):
                target = t
                break
    if target:
        rows = []
        # 抓 <tr><td>模型</td><td>数字</td><td>数字</td><td>数字</td></tr>
        for m in re.finditer(r"<tr>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>", target, re.S | re.I):
            name = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            c2 = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            c3 = re.sub(r"<[^>]+>", "", m.group(3)).strip()
            c4 = re.sub(r"<[^>]+>", "", m.group(4)).strip()
            # 跳过表头残留
            if name.lower() == "model":
                continue
            # 价格表第二列含 $，这里都是纯数字
            if "$" in c2 or "$" in c3:
                continue
            try:
                r5 = int(c2.replace(",", "").strip())
                rw = int(c3.replace(",", "").strip())
                rmth = int(c4.replace(",", "").strip())
            except:
                continue
            rows.append((name, r5, rw, rmth))
        if rows:
            return rows

    # 2) 兜底：扫描全页所有符合的 <tr> 行（兼容 markdown 形式的 | ... |）
    rows = []
    for m in re.finditer(r"<tr>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>([\d,]+)</td>\s*<td[^>]*>([\d,]+)</td>\s*<td[^>]*>([\d,]+)</td>", html, re.S):
        name = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if not name or name.lower() == "model":
            continue
        try:
            r5 = int(m.group(2).replace(",", ""))
            rw = int(m.group(3).replace(",", ""))
            rmth = int(m.group(4).replace(",", ""))
        except:
            continue
        rows.append((name, r5, rw, rmth))
    if rows:
        return rows

    # 3) 再兜底 markdown 管道表
    md_rows = []
    for line in html.splitlines():
        if "$" in line:
            continue
        rm = re.match(r"\s*\|\s*(.+?)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|", line)
        if rm:
            name = rm.group(1).strip()
            if name.lower() == "model" or name.startswith("---"):
                continue
            try:
                md_rows.append((name, int(rm.group(2).replace(",", "")), int(rm.group(3).replace(",", "")), int(rm.group(4).replace(",", ""))))
            except:
                continue
    if md_rows:
        return md_rows

    raise RuntimeError("未找到排行表格，请检查页面结构是否变更")

def load_prev():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except:
            return None
    return None

def main():
    now_bj = datetime.now(BEIJING)
    now_str = now_bj.strftime("%Y-%m-%d %H:%M (北京时间)")
    date_str = now_bj.strftime("%Y-%m-%d")

    try:
        html = fetch_md()
        rows = parse_table(html)
    except Exception as e:
        print(f"❌ 抓取/解析失败: {e}")
        print(f"URL: {URL}")
        sys.exit(3)

    # 排序：按 5小时请求数 倒序
    ranked = sorted(rows, key=lambda x: x[1], reverse=True)

    # 读取上一期用于对比
    prev = load_prev()
    prev_map = {}
    prev_rank = {}
    if prev and "ranked" in prev:
        for idx, item in enumerate(prev["ranked"], 1):
            prev_map[item["model"]] = item
            prev_rank[item["model"]] = idx

    # 构建当前期结构
    current = {
        "date": date_str,
        "fetched_at": now_bj.isoformat(),
        "source": URL,
        "ranked": [{"rank": i+1, "model": m, "per5h": p5, "perWeek": pw, "perMonth": pm} for i, (m, p5, pw, pm) in enumerate(ranked)]
    }

    # 保存状态 + 历史
    STATE_PATH.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    (HISTORY_DIR / f"{date_str}.json").write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")

    # 输出榜单（cron 投递的就是这个 stdout）
    print(f"# OpenCode Go · 每 5 小时请求数排行")
    print(f"更新时间：{now_str}  |  数据源：{URL}")
    print(f"排序：按 `requests per 5 hour` 从高到低  |  共 {len(ranked)} 款模型")
    if prev:
        print(f"对比：上一期 {prev.get('date','?')}  →  显示 排名变化 / 5h 额度变化")
    print("")
    print("| 排名 | 模型 | 5h 请求数 | 周 / 月 | 变化 |")
    print("| ---: | :--- | ---: | :--- | :--- |")

    for i, (model, p5, pw, pm) in enumerate(ranked, 1):
        change = ""
        if model in prev_rank:
            dr = prev_rank[model] - i  # 正数=上升
            dv = p5 - prev_map[model]["per5h"]
            parts = []
            if dr != 0:
                parts.append(f"{'↑' if dr>0 else '↓'}{abs(dr)}")
            else:
                parts.append("→0")
            if dv != 0:
                parts.append(f"{'+' if dv>0 else ''}{dv:,}")
            else:
                parts.append("额度不变")
            # 新模型 / 掉榜单独处理在下面
            change = " ".join(parts)
            if dr == 0 and dv == 0:
                change = "—"
        else:
            change = "🆕 新上榜" if prev else "—"

        # 周/月紧凑显示
        week_month = f"{pw:,} / {pm:,}"
        print(f"| {i} | {model} | {p5:,} | {week_month} | {change} |")

    # 掉榜检测
    if prev:
        cur_models = set(m for m,_,_,_ in ranked)
        dropped = [m for m in prev_rank if m not in cur_models]
        if dropped:
            print("")
            print(f"⚠️ 本期掉榜（上一期有、本期无）：{', '.join(dropped)}")

    print("")
    print(f"> 额度说明：Go 按 $12/5h 限额折算请求数，越便宜的模型 5h 内可跑越多。完整周/月额度见上表。")
    print(f"> 提示：每天 09:00 自动更新，数据来自 `opencode.ai/docs/go` 官方表格；若官网改版导致解析失败会直接报错提醒。")

if __name__ == "__main__":
    main()
