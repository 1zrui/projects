#!/usr/bin/env python3
"""
cron_wiki_lint.py — 知识库每日检查 纯脚本驱动入口 (no_agent cron)

直接调 wiki-daily-lint 的 lint-wiki.py，永远带 --central-index --no-write
（铁律：不碰 index.md/log.md，不自动归档误伤）。

回执只输出人话，不输出技术细节。
退出码：0 = 正常（无论有无问题，让 cron 照常投递回执）
        3 = 脚本级异常（lint 没跑起来 / 报告没生成）
"""
import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

SCRIPT = Path(
    "D:/Hermes/skills/research/wiki-daily-lint/scripts/lint-wiki.py"
).resolve()
WIKI = Path("D:/Hermes/workspace/知识库").resolve()
REPORT = WIKI / "queries" / "daily-lint-report.md"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki", default=str(WIKI))
    ap.add_argument("--today", default=date.today().isoformat())
    args = ap.parse_args()

    if not SCRIPT.exists():
        print("知识库检查失败：检查脚本找不到")
        sys.exit(3)

    cmd = [
        sys.executable, str(SCRIPT),
        "--wiki", args.wiki,
        "--today", args.today,
        "--central-index", "--no-write",
        "--report-path", "queries/daily-lint-report.md",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=600)
    except subprocess.TimeoutExpired:
        print("知识库检查失败：运行超时（10分钟）")
        sys.exit(3)

    if r.returncode != 0:
        print("知识库检查失败：检查工具自身报错")
        sys.exit(3)

    if not REPORT.exists():
        print("知识库检查失败：没生成检查报告")
        sys.exit(3)

    # 从报告抽 "发现问题数"
    text = REPORT.read_text(encoding="utf-8")
    m = re.search(r"发现问题数\s*\|\s*\*\*?(\d+)\*\*?", text)
    n = int(m.group(1)) if m else "?"

    today = date.today().isoformat()
    if n == 0:
        print(f"知识库检查完成：一切正常，没发现需要处理的問題（{today}）")
        sys.exit(0)
    else:
        print(f"知识库检查完成：发现 {n} 处需要留意的地方（{today}）")
        print("—— 问题清单 ——")
        for line in parse_issues(text):
            print(line)
        print(f"完整报告：{REPORT}")
        sys.exit(0)


def parse_issues(report_text):
    """从报告中抽取问题清单，转成中文逐条输出。"""
    # 截取 "## 问题清单" 到下一个 "##" 之间的段落
    start = report_text.find("## 问题清单")
    if start == -1:
        return ["（报告未列出明细，请打开完整报告查看）"]
    end = report_text.find("## 本次运行参数", start)
    block = report_text[start:end if end != -1 else len(report_text)]

    分类名 = {
        "1_frontmatter_missing": "缺基本信息栏(frontmatter)",
        "5_bad_tag": "标签不在规范里",
        "7_bad_date": "日期格式不对",
        "2_broken_wikilink": "失效链接",
        "3_orphan": "孤立页面(无入链)",
        "4_low_outbound": "出链太少",
        "6_oversize": "页面太长",
        "8_drift": "原始文件内容变动",
        "9_future_date": "未来日期",
        "10_index_missing": "索引缺失",
        "11_bad_type": "类型字段非法",
    }
    out = []
    cur = None
    for raw in block.splitlines():
        line = raw.strip()
        if line.startswith("### "):
            code = line[4:].strip()
            cur = 分类名.get(code, code)
            out.append(f"【{cur}】")
        elif line.startswith("- "):
            # 形如：- `concepts/xxx.md` — ['字段']
            item = line[2:].strip()
            item = item.replace("`", "")
            out.append(f"  · {item}")
    return out if out else ["（报告未列出明细，请打开完整报告查看）"]


if __name__ == "__main__":
    main()
