#!/usr/bin/env python3
"""
blockbeats_listener.py — 律动(BlockBeats)快讯实时监听 → QQ 群推送

常驻进程：每 POLL 秒拉一次快讯页(SSR HTML) → 按 id 去重 → 黑名单过滤 → 渲染成
报刊风卡片图 → 走 QQ 官方机器人(qqbot) REST 发到指定群；发图失败自动降级发文字。

设计要点
- 零第三方依赖（画卡片用 Pillow，其余全 stdlib），跨平台：Windows / Linux / macOS
- 配置全部走环境变量或 .env（见 config.example.env），密钥不进代码、不进 git
- 去重：维护 last_max_id（只推比它大的），持久化到 state 文件 → 重启不重发
- 内存稳定：state 只存一个整数，不缓存历史
- 外层自愈壳：任何未捕获异常 5 秒后自重启；配 systemd 时 Restart=always 双保险
- 拉取：先直连，失败再走代理（BB_PROXY，云服务器上一般是本机 v2rayA 端口）

命令行
  python blockbeats_listener.py                 # 常驻监听（默认）
  python blockbeats_listener.py --check         # 只抓一次并打印解析结果，不发群（部署验收用）
  python blockbeats_listener.py --once          # 只跑一轮完整流程（会发群）
  python blockbeats_listener.py --preview "标题" "正文" [--time 12:34]   # 本地渲染一张卡片图，不发群
  python blockbeats_listener.py --test-send     # 往群里发一张测试卡片（验证通道）

退出码
  0  正常退出（收到 SIGTERM / Ctrl+C）
  3  致命错误（qqbot token 获取失败等；systemd 会重启）
"""
import argparse
import base64
import json
import os
import re
import sys
import time
import uuid
import urllib.error
import urllib.request
from pathlib import Path

# ----------------------------------------------------------------------------
# 路径（默认都在项目目录内，可用环境变量覆盖）
# ----------------------------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parent


def _path(env_key: str, default: Path) -> Path:
    v = os.environ.get(env_key)
    return Path(v).expanduser() if v else default


# ----------------------------------------------------------------------------
# .env 加载（先加载，后面的配置才能读到 .env 里的值；真实环境变量优先）
# ----------------------------------------------------------------------------
def _load_env_file() -> None:
    candidates = [
        Path(os.environ["BB_ENV_FILE"]) if os.environ.get("BB_ENV_FILE") else None,
        PROJECT_DIR / ".env",
        PROJECT_DIR.parent / ".env",          # 兼容：老部署把 .env 放在上一层（如 D:/Hermes/.env）
    ]
    for path in candidates:
        if not path or not path.exists():
            continue
        try:
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and v and k not in os.environ:   # 真实环境变量优先，不被 .env 覆盖
                    os.environ[k] = v
        except Exception as e:                     # 读不到不该致命
            print(f"[warn] 读取 {path} 失败: {e}", flush=True)
        break


_load_env_file()

STATE_FILE = _path("BB_STATE_FILE", PROJECT_DIR / "state" / "last_id.json")
LOG_FILE = _path("BB_LOG_FILE", PROJECT_DIR / "logs" / "listener.log")
CACHE_DIR = _path("BB_CACHE_DIR", PROJECT_DIR / "cache")

SOURCE_URL = os.environ.get("BB_SOURCE_URL", "https://www.theblockbeats.info/newsflash/rss")
POLL = max(5, int(os.environ.get("BB_POLL", "20")))
PROXY_URL = os.environ.get("BB_PROXY", "").strip()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}

# ---- qqbot 官方通道 ----
QQBOT_API_BASE = os.environ.get("QQBOT_API_BASE", "https://api.sgroup.qq.com")
QQBOT_TOKEN_URL = os.environ.get("QQBOT_TOKEN_URL", "https://bots.qq.com/app/getAppAccessToken")
GROUP_OPENID = os.environ.get("BB_GROUP_OPENID", "8DDF1613C07205222566826C231D9201")  # 数字群 631502972
QQ_APP_ID_DEFAULT = os.environ.get("QQ_APP_ID", "")
_TOKEN_CACHE = {"token": None, "expires_at": 0.0}

# ---- 字体（跨平台自动探测；可用 BB_FONT_REGULAR / BB_FONT_BOLD 指定）----
FONT_CANDIDATES_REGULAR = [
    os.environ.get("BB_FONT_REGULAR", ""),
    # Linux（Ubuntu/Debian: apt install fonts-noto-cjk）
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
    # Windows
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    # macOS
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
]
FONT_CANDIDATES_BOLD = [
    os.environ.get("BB_FONT_BOLD", ""),
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Bold.otf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc",
]


def find_font(candidates) -> str:
    """返回第一个存在的字体路径；都没有则返回空串（会退化成默认字体，中文可能显示方块）。"""
    for c in candidates:
        if c and Path(c).exists():
            return c
    return ""


# ---- 过滤：默认全发，只拦明显非币圈的生活/泛新闻 ----
BLACKLIST = ["世界杯", "演唱会", "综艺", "电影", "电视剧", "奥运", "欧冠", "NBA",
             "股票", "A股", "港股", "美股三大指数", "天气", "地震", "选秀", "明星",
             "球赛", "彩票", "体彩"]
HTML_TAG = re.compile(r"<[^>]+>")


# ----------------------------------------------------------------------------
# 基础工具
# ----------------------------------------------------------------------------
def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def clean(html) -> str:
    return HTML_TAG.sub("", html or "").strip()


def unescape(s: str) -> str:
    return (s.replace("&amp;", "&").replace("&quot;", '"').replace("&lt;", "<")
             .replace("&gt;", ">").replace("&#39;", "'").replace("&nbsp;", " "))


def load_state() -> int:
    if STATE_FILE.exists():
        try:
            return int(json.loads(STATE_FILE.read_text(encoding="utf-8")).get("last_max_id", 0))
        except Exception:
            pass
    return 0


def save_state(last_max_id: int) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"last_max_id": int(last_max_id)}, ensure_ascii=False),
                          encoding="utf-8")


def is_relevant(title, content) -> bool:
    """BlockBeats 本身是加密快讯源 → 默认全发，仅黑名单拦非币圈。"""
    text = f"{title or ''} {content or ''}"
    return not any(kw in text for kw in BLACKLIST)


# ----------------------------------------------------------------------------
# 抓取 + 解析（SSR 页面；旧 REST API 已于 2026-08-30 废弃）
# ----------------------------------------------------------------------------
def _open(url: str, timeout: int = 25, use_proxy: bool = False):
    req = urllib.request.Request(url, headers=UA)
    handlers = [urllib.request.ProxyHandler({"http": PROXY_URL, "https": PROXY_URL})] if (use_proxy and PROXY_URL) \
        else [urllib.request.ProxyHandler({})]
    return urllib.request.build_opener(*handlers).open(req, timeout=timeout)


def fetch_flashes() -> list:
    """抓快讯列表页并解析。返回 [{id,title,content,link,time}]（按 id 升序）。"""
    last_err = None
    try:
        with _open(SOURCE_URL) as r:
            return _parse_page(r.read().decode("utf-8", "ignore"))
    except Exception as e:
        last_err = e
        print(f"[warn] 直连拉取失败({type(e).__name__}: {e})" + ("，尝试代理兜底" if PROXY_URL else ""), flush=True)
    if PROXY_URL:
        try:
            with _open(SOURCE_URL, use_proxy=True) as r:
                return _parse_page(r.read().decode("utf-8", "ignore"))
        except Exception as e:
            last_err = e
            print(f"[err] 代理也失败({type(e).__name__}: {e})，本轮跳过", flush=True)
    raise last_err if last_err else RuntimeError("未知拉取错误")


def _parse_page(raw: str) -> list:
    """抠每条快讯：/flash/{id} + 标题 + HH:MM + 正文(news-flash-item-content > p)。"""
    items, seen = [], set()
    for blk in re.finditer(
        r'<div class="news-flash-wrapper"[^>]*>(.*?)'
        r'(?=<div class="news-flash-wrapper"|</div></div></div>\s*$)', raw, re.S):
        seg = blk.group(1)
        am = re.search(r'href="/flash/(\d+)"[^>]*?>(.*?)</a>', seg, re.S)
        if not am:
            continue
        fid = int(am.group(1))
        if fid in seen:
            continue
        inner = am.group(2)
        tm = re.search(r'title="([^"]*)"', inner) or re.search(r'news-flash-title-text[^>]*>([^<]+)</div>', inner)
        if not tm:
            continue
        title = unescape(tm.group(1).strip())
        tmm = re.search(r'(\d{1,2}:\d{2})', inner)
        tstr = tmm.group(1) if tmm else ""
        cm = re.search(r'news-flash-item-content[^>]*>\s*<p>(.*?)</p>', seg, re.S)
        content = unescape(re.sub(r'<[^>]+>', '', cm.group(1))) if cm else ""
        seen.add(fid)
        items.append({"id": fid, "title": title, "content": content,
                      "link": f"https://www.theblockbeats.info/flash/{fid}", "time": tstr})
    items.sort(key=lambda x: x["id"])
    return items


# ----------------------------------------------------------------------------
# 卡片渲染（报刊风，Pillow 直画，全文不截断）
# ----------------------------------------------------------------------------
def render_image(item_id, title, content, link, tstr="", out_path: Path = None):
    """渲染卡片图，返回本地路径；失败返回 None（调用方降级发文字）。"""
    try:
        from PIL import Image, ImageDraw, ImageFont

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
            safe = []
            for ln in lines:
                while font.getlength(ln) > max_w and len(ln) > 1:
                    ln = ln[:-1]
                safe.append(ln)
            return safe

        fpath, fbold = find_font(FONT_CANDIDATES_REGULAR), find_font(FONT_CANDIDATES_BOLD)
        if not fpath or not fbold:
            log("[warn] 未找到中文字体（Linux 请 apt install fonts-noto-cjk，"
                "或用 BB_FONT_REGULAR/BB_FONT_BOLD 指定 .ttc/.otf 路径），中文可能显示为方块")
        try:
            F, FB = (fpath or fbold), (fbold or fpath)
            f12 = ImageFont.truetype(F, 12); f13 = ImageFont.truetype(F, 13)
            fb13 = ImageFont.truetype(FB or F, 13); f16 = ImageFont.truetype(F, 16)
            fb16 = ImageFont.truetype(FB or F, 16); fb28 = ImageFont.truetype(FB or F, 28)
        except Exception as e:
            log(f"[warn] 字体加载失败({e})，用 Pillow 默认字体")
            f12 = f13 = fb13 = f16 = fb16 = fb28 = ImageFont.load_default()

        W, PAD_L, PAD_R = 640, 44, 44
        BW = W - PAD_L - PAD_R

        body = content or ""
        m = re.match(r"^BlockBeats\s*消息[，,]\s*(.*)", body)   # 去掉导语前缀
        if m:
            body = m.group(1)

        title_lines = wrap(title or "", fb28, BW)
        body_lines = wrap(body, f16, BW)
        link_lines = wrap(link or "", f12, BW)

        H = max(36 + 30 + len(title_lines) * 40 + 20 + len(body_lines) * 26 + 36 + 24, 200)
        img = Image.new("RGB", (W, H), (242, 238, 232))
        d = ImageDraw.Draw(img)

        y = 24
        d.rounded_rectangle([PAD_L, y, PAD_L + 28, y + 20], radius=3, fill=(200, 50, 40))
        d.text((PAD_L + 14, y + 10), "F", font=fb13, fill=(255, 255, 255), anchor="mm")
        if tstr:
            d.text((W - PAD_R, y + 10), tstr, font=f13, fill=(140, 135, 128), anchor="rm")
        y += 30
        for ln in title_lines:
            d.text((PAD_L, y), ln, font=fb28, fill=(30, 28, 25)); y += 40
        y += 8
        d.rectangle([PAD_L, y, PAD_L + 40, y + 3], fill=(200, 80, 30)); y += 16
        for ln in body_lines:
            d.text((PAD_L, y), ln, font=f16, fill=(45, 42, 38)); y += 26
        if link_lines:
            y += 14
            for ln in link_lines:
                d.text((PAD_L, y), ln, font=f12, fill=(90, 120, 200)); y += 18
        y += 16
        d.text((PAD_L, y), "BlockBeats · 实时推送", font=f12, fill=(150, 145, 138))

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        src = Path(out_path) if out_path else (CACHE_DIR / f"flash_{item_id}.png")
        img.save(src, "PNG")
        return str(src)
    except Exception as e:
        log(f"[warn] 渲染图片失败，将降级发文字: {type(e).__name__}: {e}")
        return None


# ----------------------------------------------------------------------------
# qqbot 官方 REST
# ----------------------------------------------------------------------------
def get_qqbot_token() -> str:
    now = time.time()
    if _TOKEN_CACHE["token"] and now < _TOKEN_CACHE["expires_at"] - 60:
        return _TOKEN_CACHE["token"]
    app_id = os.environ.get("QQ_APP_ID") or QQ_APP_ID_DEFAULT
    secret = os.environ.get("QQ_CLIENT_SECRET")
    if not app_id or not secret:
        raise RuntimeError("缺少 QQ_APP_ID / QQ_CLIENT_SECRET（写进 .env 或 systemd EnvironmentFile）")
    req = urllib.request.Request(
        QQBOT_TOKEN_URL,
        data=json.dumps({"appId": app_id, "clientSecret": secret}).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read().decode("utf-8"))
    tok = d.get("access_token")
    if not tok:
        raise RuntimeError(f"qqbot token 获取失败: {d}")
    _TOKEN_CACHE["token"] = tok
    _TOKEN_CACHE["expires_at"] = now + float(d.get("expires_in", 3600))
    return tok


def qqbot_api(method: str, path: str, payload: dict, timeout: int = 60) -> dict:
    token = get_qqbot_token()
    req = urllib.request.Request(
        f"{QQBOT_API_BASE}{path}", data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"QQBot {token}", "Content-Type": "application/json"},
        method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"qqbot API {path} HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}")


def _seq() -> int:
    return (int(time.time()) ^ int(uuid.uuid4().hex[:4], 16)) % 65536


def send_qq_image(item_id, title, content, link, tstr="") -> bool:
    """优先发图；出图/上传/发消息任一步失败 → 降级发全文文字。"""
    img_path = render_image(item_id, title, content, link, tstr)
    if img_path:
        try:
            b64 = base64.b64encode(Path(img_path).read_bytes()).decode("ascii")
            up = qqbot_api("POST", f"/v2/groups/{GROUP_OPENID}/files",
                           {"file_type": 1, "file_data": b64, "srv_send_msg": False}, timeout=120)
            fi = up.get("file_info") or (up.get("data") or {}).get("file_info")
            if not fi:
                raise RuntimeError(f"上传未返回 file_info: {str(up)[:200]}")
            qqbot_api("POST", f"/v2/groups/{GROUP_OPENID}/messages",
                      {"msg_type": 7, "media": {"file_info": fi}, "msg_seq": _seq()})
            log(f"推送图片 id={item_id} 发送=OK | {title[:40]}")
            return True
        except Exception as e:
            log(f"[warn] qqbot 图片链路失败({type(e).__name__}: {e})，降级发文字")
    text = f"【BlockBeats 快讯】{'⏰' + tstr + '  ' if tstr else ''}{title}\n{content}"
    if link:
        text += f"\n{link}"
    return send_qq_text(text)


def send_qq_text(text: str) -> bool:
    try:
        qqbot_api("POST", f"/v2/groups/{GROUP_OPENID}/messages",
                  {"content": (text or "")[:4000], "msg_type": 0, "msg_seq": _seq()})
        return True
    except Exception as e:
        log(f"[warn] qqbot 文字发送异常: {e}")
        return False


# ----------------------------------------------------------------------------
# 主循环
# ----------------------------------------------------------------------------
def poll_once(last_max_id: int) -> int:
    """抓一轮 + 推新条目，返回新的 last_max_id。"""
    arr = fetch_flashes()
    if not arr:
        return last_max_id
    new = sorted([it for it in arr if it.get("id", 0) > last_max_id], key=lambda x: x["id"])
    for it in new:
        title, content = it.get("title", ""), clean(it.get("content", ""))
        if not is_relevant(title, content):
            log(f"跳过(不相关) id={it['id']} | {title[:40]}")
            continue                                   # 不相关的也推进度（见循环尾），但留痕
        ok = send_qq_image(it["id"], title, content, it.get("link", ""), it.get("time", ""))
        log(f"推送 id={it['id']} 发送={'OK' if ok else 'FAIL'} | {title[:40]}")
        last_max_id = it["id"]
        save_state(last_max_id)                        # 每条真正发完才推进（防静默丢快讯）
    if new:
        newest = max(it["id"] for it in new)
        if newest > last_max_id:                       # 全部被过滤时也要推进，避免反复重拉
            last_max_id = newest
            save_state(last_max_id)
    return last_max_id


def run_daemon() -> None:
    last_max_id = load_state()
    log(f"启动监听 | 源={SOURCE_URL} | 目标群openid={GROUP_OPENID[:8]}... | 间隔={POLL}s | "
        f"last_max_id={last_max_id} | 代理={PROXY_URL or '无'}")
    try:
        get_qqbot_token()
        log("qqbot token 获取成功，通道就绪")
    except Exception as e:
        log(f"[fatal] qqbot token 获取失败: {e}")
        sys.exit(3)
    while True:
        try:
            last_max_id = poll_once(last_max_id)
        except Exception as e:
            log(f"[err] 本轮异常: {type(e).__name__}: {e}")
        time.sleep(POLL)


def main() -> None:
    ap = argparse.ArgumentParser(description="律动(BlockBeats)快讯 → QQ群 推送")
    ap.add_argument("--check", action="store_true", help="只抓一次并打印解析结果，不发群（部署验收）")
    ap.add_argument("--once", action="store_true", help="只跑一轮完整流程（会发群）")
    ap.add_argument("--preview", nargs="*", help='本地渲染卡片图不发群：--preview "标题" "正文" [--time HH:MM]')
    ap.add_argument("--time", default="", help="--preview 用的时间文本")
    ap.add_argument("--out", default="", help="--preview 输出图片路径")
    ap.add_argument("--test-send", action="store_true", help="往群里发一张测试卡片（验证通道）")
    args = ap.parse_args()

    if args.check:
        arr = fetch_flashes()
        print(f"[check] 抓取成功，解析到 {len(arr)} 条")
        for it in arr[:5]:
            print(f"  id={it['id']} {it['time']:>5} | {it['title'][:48]} | 正文 {len(it['content'])} 字 | 相关={is_relevant(it['title'], it['content'])}")
        if arr:
            print(f"  ↑ 最新 id={arr[-1]['id']}，本地 state last_max_id={load_state()}")
        print(f"[check] 字体: regular={find_font(FONT_CANDIDATES_REGULAR) or '未找到(中文会显示方块!)'} | "
              f"bold={find_font(FONT_CANDIDATES_BOLD) or '未找到'}")
        sys.exit(0)          # 一次性模式必须显式退出，否则外层自愈壳会把它当崩溃无限重启
        return

    if args.preview is not None and args.preview:
        title = args.preview[0] if len(args.preview) > 0 else "示例标题"
        content = args.preview[1] if len(args.preview) > 1 else ""
        out = args.out or str(CACHE_DIR / "preview.png")
        p = render_image("preview", title, content, "https://www.theblockbeats.info/flash/000000",
                         args.time or time.strftime("%H:%M"), out_path=out)
        print(f"[preview] 图片已生成: {p}" if p else "[preview] 渲染失败")
        sys.exit(0 if p else 1)

    if args.test_send:
        ts = time.strftime("%H:%M")
        ok = send_qq_image("test", "【通道测试】律动推送部署完成",
                           f"这是一条测试卡片，收到即说明 qqbot 通道正常。发送时间 {ts}。", "", ts)
        print(f"[test-send] 发送{'成功' if ok else '失败'}")
        sys.exit(0 if ok else 3)

    if args.once:
        last = load_state()
        try:
            get_qqbot_token()
        except Exception as e:
            log(f"[fatal] qqbot token 获取失败: {e}")
            sys.exit(3)
        new_last = poll_once(last)
        print(f"[once] 完成，last_max_id: {last} → {new_last}")
        sys.exit(0)

    run_daemon()


if __name__ == "__main__":
    # 外层自愈壳：main() 任何未捕获异常/非零退出 → 5 秒后自重启（systemd 下是双保险）
    import traceback
    while True:
        try:
            main()
            log("[fatal] main() 意外返回，5 秒后重启")
        except KeyboardInterrupt:
            log("收到中断，退出")
            sys.exit(0)
        except SystemExit as e:
            if e.code in (0, None):
                sys.exit(0)
            log(f"[fatal] SystemExit code={e.code}，5 秒后重启")
            log(traceback.format_exc())
        except Exception as e:
            log(f"[fatal] 未捕获异常: {type(e).__name__}: {e}，5 秒后重启")
            log(traceback.format_exc())
        time.sleep(5)
        log(">>> 外层重启 main() <<<")
