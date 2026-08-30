#!/usr/bin/env python3
"""
blockbeats_listener.py — BlockBeats 快讯实时监听（常驻进程）

每 30 秒拉 api-pro.theblockbeats.info/v1/newsflash（走 10808 代理），
按 id 去重，关键词过滤"对加密走势有影响"的快讯，命中立即发 QQ(2415317075)。

设计要点：
- key 不写死，从 .blockbeats_key 读取
- 去重：维护 last_max_id（自增 id，新>旧），只推比它大的
- 重启不重发：last_max_id 持久化到 .blockbeats_state.json
- 内存稳定：只存一个整数，不缓存历史
- 纯 REST 拉取，非推送，最快延迟=拉取间隔(30s)，已实测 RSS≈25MB

退出码：
  0 正常退出（收到 SIGTERM 等）
  3 致命错误（NapCat 不通 / key 缺失 且 3 次重试失败）
"""
import json
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
KEY_FILE = SCRIPT_DIR / ".blockbeats_key"
STATE_FILE = SCRIPT_DIR / ".blockbeats_state.json"
LOG_FILE = SCRIPT_DIR / "blockbeats_listener.log"

API = "https://api-pro.theblockbeats.info/v1/newsflash?page=1&size=20&lang=cn"
PROXY = {"http": "http://127.0.0.1:10808", "https": "http://127.0.0.1:10808"}
POLL = 30                      # 拉取间隔(秒)
QQ_TARGET = "445141066"          # 推送目标群（起源之地）
NAP_BASE = "http://127.0.0.1:18801"

# 对加密走势有影响的快讯关键词（命中才推，省得融资稿刷屏）
# 只保留"事件驱动型强信号"。注意：普通交易所动态（Circle在XX上线USDC、某链TVL增长）
# 不算强事件，所以交易所名、链名、"上线"泛词都不放，避免滤了个寂寞。
KEYWORDS = [
    # 新币上大所（真正"上所"事件）
    "上所", "上币", "开通交易", "上线交易",
    # 监管/政策
    "SEC", "CFTC", "证监会", "监管", "央行", "美联储",
    "降息", "加息", "利率", "ETF", "批准", "获批", "通过", "拒绝",
    # 巨鲸/大额异动
    "巨鲸", "大户", "转移", "转入", "转出", "异动",
    # 黑天鹅/安全事故
    "黑天鹅", "暴雷", "宕机", "黑客", "被盗", "失窃", "封禁", "冻结",
    # 法律/地缘
    "诉讼", "起诉", "指控", "制裁", "关税",
    # 杠杆/衍生品强信号
    "清算", "爆仓", "插针", "最大痛点", "期权到期",
    # 代币供应事件
    "空投", "解锁", "减半", "分叉", "fork",
    # 价格极端
    "暴跌", "暴涨",
    # 稳定币脱锚（特有强信号）
    "脱锚", "depeg",
]

HTML_TAG = re.compile(r"<[^>]+>")


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_key():
    # 优先从集中保险箱 .env 读（所有 key 统一存放）
    env_path = SCRIPT_DIR.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("BLOCKBEATS_API_KEY="):
                v = line.split("=", 1)[1].strip().strip('"').strip("'")
                if v:
                    return v
    # 兼容旧分散文件（过渡期）
    if KEY_FILE.exists():
        return KEY_FILE.read_text(encoding="utf-8").strip()
    raise SystemExit("缺少 key：.env 无 BLOCKBEATS_API_KEY 且 .blockbeats_key 不存在")


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8")).get("last_max_id", 0)
        except Exception:
            pass
    return 0


def save_state(last_max_id):
    STATE_FILE.write_text(json.dumps({"last_max_id": last_max_id}, ensure_ascii=False),
                          encoding="utf-8")


def fetch_flashes(key):
    req = urllib.request.Request(API, headers={"api-key": key})
    last_err = None
    # 1) 优先直连（api-pro 直连稳定，绕过 10808 代理 SSL 抖动）
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=25) as r:
            d = json.loads(r.read().decode("utf-8"))
        if d.get("status") != 0:
            raise RuntimeError(f"API 返回异常 status={d.get('status')} msg={d.get('message')}")
        return d.get("data", {}).get("data", []) if isinstance(d.get("data"), dict) else []
    except Exception as e:
        last_err = e
        print(f"[warn] 直连拉取失败({type(e).__name__})，尝试代理兜底", flush=True)
    # 2) 直连失败 → 走代理
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler(PROXY))
        with opener.open(req, timeout=25) as r:
            d = json.loads(r.read().decode("utf-8"))
        if d.get("status") != 0:
            raise RuntimeError(f"API 返回异常 status={d.get('status')} msg={d.get('message')}")
        return d.get("data", {}).get("data", []) if isinstance(d.get("data"), dict) else []
    except Exception as e:
        last_err = e
        print(f"[err] 代理也失败({type(e).__name__})，本轮跳过", flush=True)
    raise last_err if last_err else RuntimeError("未知拉取错误")


def is_relevant(title, content):
    # 只扫标题：BlockBeats 标题已高度概括，标题命中=真事件；
    # content 里的"通过/批准/空投"等是叙述噪音，扫 content 会大量误杀。
    text = title or ""
    return any(kw.lower() in text.lower() for kw in KEYWORDS)


def clean(html):
    return HTML_TAG.sub("", html or "").strip()


def render_image(item_id, title, content, link):
    """把快讯渲染成卡片图，返回图片本地路径；失败返回 None（调用方降级发文字）。"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import shutil

        FONT = "C:/Windows/Fonts/msyh.ttc"
        try:
            f_title = ImageFont.truetype(FONT, 30)
            f_body = ImageFont.truetype(FONT, 22)
            f_meta = ImageFont.truetype(FONT, 16)
        except Exception:
            f_title = ImageFont.load_default()
            f_body = ImageFont.load_default()
            f_meta = ImageFont.load_default()

        # 画布：宽 720，先按内容估计高度
        W = 720
        PAD = 32
        LINE = 34
        # 通用换行：必须用传入的 font 算宽度（标题/正文/链接字号不同）
        def wrap(text, font, max_w):
            lines, cur = [], ""
            for ch in text:
                if ch == "\n":
                    lines.append(cur); cur = ""; continue
                t = (cur + ch)
                # 用当前字体实测宽度；超宽则换行（保留已排字符）
                if font.getlength(t) > max_w and cur:
                    lines.append(cur); cur = ch
                else:
                    cur = t
            if cur:
                lines.append(cur)
            # 兜底：极少数超宽字符（如长URL/emoji）仍可能溢出，硬截断保安全
            safe = []
            for ln in lines:
                while font.getlength(ln) > max_w and len(ln) > 1:
                    ln = ln[:-1]
                safe.append(ln)
            return safe

        title_lines = wrap(title or "", f_title, W - 2 * PAD)
        body_lines = wrap(content or "", f_body, W - 2 * PAD)
        link_lines = wrap(link or "", f_meta, W - 2 * PAD)

        H = PAD + len(title_lines) * 42 + 16 + len(body_lines) * LINE \
            + (20 + len(link_lines) * 22 if link_lines else 0) + PAD + 40
        H = max(H, 200)

        img = Image.new("RGB", (W, int(H)), (18, 20, 28))
        d = ImageDraw.Draw(img)
        # 顶部色条
        d.rectangle([0, 0, W, 8], fill=(255, 120, 0))
        y = PAD
        # 标题
        for ln in title_lines:
            d.text((PAD, y), ln, font=f_title, fill=(255, 180, 60))
            y += 42
        y += 16
        # 正文
        for ln in body_lines:
            d.text((PAD, y), ln, font=f_body, fill=(235, 235, 235))
            y += LINE
        # 链接/来源
        if link_lines:
            y += 20
            for ln in link_lines:
                d.text((PAD, y), ln, font=f_meta, fill=(140, 170, 255))
                y += 22
        # 底部署名
        d.text((PAD, int(H) - PAD - 20), "BlockBeats 快讯 · 实时推送",
               font=f_meta, fill=(120, 120, 120))

        cache = SCRIPT_DIR / "blockbeats_cache"
        cache.mkdir(exist_ok=True)
        src = cache / f"flash_{item_id}.png"
        img.save(src, "PNG")
        # 发图铁律：必须 cp 到 Downloads 再用 file:/// 发
        dst = Path("C:/Users/Administrator/Downloads") / src.name
        shutil.copyfile(src, dst)
        return str(dst)
    except Exception as e:
        log(f"[warn] 渲染图片失败，将降级发文字: {e}")
        return None


def send_qq_image(item_id, title, content, link):
    """优先发图片；图片失败则降级为文字。"""
    import urllib.request as u
    img_path = render_image(item_id, title, content, link)
    if img_path:
        payload = json.dumps({
            "group_id": int(QQ_TARGET),
            "message": [{"type": "image", "data": {"file": f"file:///{img_path}"}}]
        }, ensure_ascii=False).encode("utf-8")
        req = u.Request(f"{NAP_BASE}/send_msg", data=payload,
                        headers={"Content-Type": "application/json"}, method="POST")
        for attempt in range(1, 4):
            try:
                with u.urlopen(req, timeout=15) as r:
                    d = json.loads(r.read().decode("utf-8"))
                if d.get("retcode") == 0:
                    return True
                log(f"[warn] 图片发送返回 retcode={d.get('retcode')} (尝试{attempt})")
            except Exception as e:
                log(f"[warn] 图片发送异常: {e} (尝试{attempt})")
            if attempt < 3:
                time.sleep(3)
        log("[warn] 图片发送失败，降级发文字")
    # 降级：原文字逻辑（保留全文，不再截断）
    text = f"【BlockBeats 快讯】{title}\n{content}"
    if link:
        text += f"\n{link}"
    return send_qq_text(text)


def send_qq_text(text):
    import urllib.request as u
    payload = json.dumps({"group_id": int(QQ_TARGET), "message": text}).encode("utf-8")
    req = u.Request(f"{NAP_BASE}/send_msg", data=payload,
                    headers={"Content-Type": "application/json"}, method="POST")
    for attempt in range(1, 4):
        try:
            with u.urlopen(req, timeout=15) as r:
                d = json.loads(r.read().decode("utf-8"))
            if d.get("retcode") == 0:
                return True
            log(f"[warn] 发送返回 retcode={d.get('retcode')} (尝试{attempt})")
        except Exception as e:
            log(f"[warn] 发送异常: {e} (尝试{attempt})")
        if attempt < 3:
            time.sleep(3)
    return False


def main():
    key = load_key()
    last_max_id = load_state()
    log(f"启动 BlockBeats 监听 | 目标QQ={QQ_TARGET} | 间隔={POLL}s | last_max_id={last_max_id}")

    # 启动先探 NapCat 连通
    try:
        urllib.request.urlopen(f"{NAP_BASE}/get_login_info", timeout=5)
    except Exception as e:
        log(f"[fatal] NapCat 不通: {e}")
        sys.exit(3)

    while True:
        try:
            arr = fetch_flashes(key)
            if not arr:
                time.sleep(POLL)
                continue
            # 按 id 降序（API 默认最新在前），取新于 last_max_id 的
            new = [it for it in arr if it.get("id", 0) > last_max_id]
            new.sort(key=lambda x: x["id"])  # 旧的先发
            for it in new:
                title = it.get("title", "")
                content = clean(it.get("content", ""))
                if not is_relevant(title, content):
                    continue
                link = it.get("link", "")
                ok = send_qq_image(it["id"], title, content, link)
                log(f"推送 id={it['id']} 相关={'是'} 发送={'OK' if ok else 'FAIL'} | {title[:40]}")
            if new:
                last_max_id = max(it["id"] for it in new)
                save_state(last_max_id)
        except Exception as e:
            log(f"[err] 本轮异常: {e}")
        time.sleep(POLL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("收到中断，退出")
        sys.exit(0)
