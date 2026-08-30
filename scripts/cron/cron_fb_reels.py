#!/usr/bin/env python3
"""
cron_fb_reels.py — FB Reels 定时任务纯脚本驱动入口 (no_agent cron)

替代 LLM 驱动：check → download → transcode → send 全流程由脚本固定执行，
杜绝 LLM 误读退出码导致的漏视频问题 (2026-08-14 根治)。

输出（stdout）即回执，由 cron 直接投递：
- 无新视频:  简短一行
- 有新视频:  发现/下载/转码/发送 数字 + 发送文件名
- 异常:      退出码 + 原因 (cron 会发错误告警)

退出码：
  0 = 正常（无论有无新视频）
  3 = 管线异常（check/download/transcode/send 任一失败）
"""
import argparse, json, subprocess, sys
from pathlib import Path
from datetime import datetime

# 注意：本脚本由 cron 从 D:/Hermes/scripts/ 调用，兄弟脚本在 skill 目录，
# 必须显式指向 skill 的 scripts 目录（不能用 __file__ 所在目录）。
SCRIPTS = Path("D:/Hermes/skills/social-media/fb-reels-douyin-sender/scripts").resolve()
FB_URL = "https://www.facebook.com/profile.php?id=61560682054555&sk=reels_tab"
STATE = Path("D:/fb_reels_links/state.json")
WORK = Path("D:/Downloads/fb_reels_pipeline")
TARGET = "2415317075"


def run(cmd, desc, timeout=600):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {desc} ...", flush=True)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return r
    except subprocess.TimeoutExpired:
        print(f"[err] {desc} 超时 {timeout}s", flush=True)
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=TARGET)
    ap.add_argument("--skip-send", action="store_true", help="只下载转码不发送（测试用）")
    args = ap.parse_args()

    raw_dir = WORK / "raw"
    dy_dir = WORK / "dy"
    raw_dir.mkdir(parents=True, exist_ok=True)
    dy_dir.mkdir(parents=True, exist_ok=True)

    # ===== 1. check =====
    r = run([sys.executable, str(SCRIPTS / "check_reels.py"),
             "--url", FB_URL, "--state", str(STATE)], "检查新 Reels")
    if r is None:
        sys.exit(3)
    check_out = r.stdout
    if r.returncode == 1:
        # 无新视频
        print("无新视频，不下载。")
        sys.exit(0)
    elif r.returncode == 0:
        # 有新增，抽取新增数量
        import re
        m = re.search(r"实际新增 \(跳过置顶\): (\d+)", check_out)
        new_cnt = int(m.group(1)) if m else "?"
        print(f"发现 {new_cnt} 条新视频，进入下载流程。")
    else:
        # 2/3/4/5 = 异常
        reasons = {2: "state.json 不存在", 3: "抓取失败/超时/FB 不可达",
                   4: "找不到 Chrome", 5: "Chrome 启动超时"}
        print(f"[err] check_reels 异常 (rc={r.returncode}): {reasons.get(r.returncode, '未知')}")
        sys.exit(3)

    # ===== 2. download =====
    r = run([sys.executable, str(SCRIPTS / "download_reels.py"),
             str(STATE), str(raw_dir), "5", "120"], "下载新视频")
    if r is None:
        sys.exit(3)
    dl_out = r.stdout
    dl_cnt = 0
    import re
    m = re.search(r"完成：(\d+) 下载", dl_out)
    if m:
        dl_cnt = int(m.group(1))

    # ===== 2.5 自动标记超时跳过的视频（2026-08-14 大哥要求）=====
    # download 输出 [skip] <rid>: <时长> > <上限>s → 提取 rid 写入 state.skipped_reel_ids，
    # 之后 check 基线并入 skipped，不再每轮重复报"发现新视频但超时长"。
    skip_ids = re.findall(r"\[skip\] (\d{10,}):", dl_out)
    if skip_ids:
        try:
            state = json.loads(STATE.read_text(encoding="utf-8"))
            skipped = set(state.get("skipped_reel_ids") or [])
            for rid in skip_ids:
                skipped.add(rid)
            state["skipped_reel_ids"] = sorted(skipped)
            STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[auto-skip] 已将 {len(skip_ids)} 条超时视频标记跳过: {skip_ids}")
        except Exception as e:
            print(f"[warn] 自动标记跳过失败: {e}")

    # 下载失败也继续转码（可能有部分下载成功）

    # ===== 3. transcode =====
    r = run([sys.executable, str(SCRIPTS / "transcode_for_douyin.py"),
             str(raw_dir), str(dy_dir)], "转码抖音兼容格式")
    if r is None:
        sys.exit(3)
    tc_out = r.stdout
    tc_ok = tc_fail = 0
    m = re.search(r"完成：(\d+) 成功, (\d+) 失败", tc_out)
    if m:
        tc_ok, tc_fail = int(m.group(1)), int(m.group(2))

    # ===== 4. send =====
    sent_ok = sent_fail = 0
    if args.skip_send:
        print("(测试模式 --skip-send，未发送)")
    else:
        r = run([sys.executable, str(SCRIPTS / "send_files_to_qq.py"),
                 str(dy_dir), "--target", args.target], f"发送到 QQ {args.target}")
        if r is not None:
            m = re.search(r"(\d+) 成功 / (\d+) 失败", r.stdout)
            if m:
                sent_ok, sent_fail = int(m.group(1)), int(m.group(2))

    # ===== 5. 归档清场 =====
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        arch = WORK / f"_archive_sent_{ts}"
        arch.mkdir(parents=True, exist_ok=True)
        for f in list(raw_dir.glob("*.mp4")) + list(dy_dir.glob("*.mp4")):
            import shutil
            shutil.copy2(f, arch / f.name)
        for f in list(raw_dir.glob("*.mp4")) + list(raw_dir.glob("*.json")) + list(dy_dir.glob("*.mp4")):
            f.unlink(missing_ok=True)
    except Exception as e:
        print(f"[warn] 归档清场失败: {e}")

    # ===== 回执 =====
    print()
    # 全超时长场景：check 报新增但下载 0 → 说明新增视频全部超 120s（Pitfall #14 预期行为）
    if dl_cnt == 0 and tc_ok == 0 and sent_ok == 0:
        print(f"发现 {new_cnt} 条新视频，但全部超 120s 时长已跳过（不会重复发，每轮会重复检测）")
        print(f"跳过视频ID: 见 check 输出")
        print(f"下载 {dl_cnt} 条 | 转码 {tc_ok} 成功 {tc_fail} 失败 | 发送 {sent_ok} 成功 {sent_fail} 失败")
        sys.exit(0)
    print(f"发现 {new_cnt} 条新视频 | 下载 {dl_cnt} 条 | 转码 {tc_ok} 成功 {tc_fail} 失败 | 发送 {sent_ok} 成功 {sent_fail} 失败")
    if sent_ok > 0:
        sent_files = [f.name for f in dy_dir.glob("*.mp4")]
        # 已清场，从归档里读
        print(f"已发送到 QQ {args.target}")

    # 发送失败视为异常
    if sent_fail > 0 or (tc_fail > 0 and dl_cnt > 0):
        print(f"[err] 存在失败项：转码失败 {tc_fail}，发送失败 {sent_fail}")
        sys.exit(3)

    sys.exit(0)


if __name__ == "__main__":
    main()
