#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BSC meme 监控 v2 — 双数据源 + 去重报警 + QQ群推送
================================================
数据源:
  1. DexScreener boosts/profiles 流 (推广位精准发现)
  2. GeckoTerminal trending pools (BSC链热门池，量大)
发现: 两源并查 → 新币入池盯盘
盯盘: 每轮快照对比 → 急拉/急砸/大涨/撤池/放量
推送: 报警实时推送到QQ群

用法:
  python3 bsc_meme_monitor.py          # 单次扫描（适合 cron）
  python3 bsc_meme_monitor.py --loop   # 常驻循环（默认3分钟一轮）
依赖: 纯标准库，零第三方依赖
"""
import json, sys, time, urllib.request, urllib.parse, ssl, datetime, os, random

BASE = os.path.dirname(os.path.abspath(__file__))
CFG_FILE = os.path.join(BASE, "bsc_config.json")
EVENTS = os.path.join(BASE, "bsc_events.jsonl")
WATCH = os.path.join(BASE, "bsc_watch.json")

CFG = json.load(open(CFG_FILE, encoding="utf-8"))

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# ── QQ Bot 推送 ─────────────────────────────────────────
QQ_APP_ID = os.environ.get("QQ_APP_ID", "1905595541")
QQ_SECRET = os.environ.get("QQ_CLIENT_SECRET", "wEWp8Sm7TpCayNnDe6Y1VzU0W3b9iItU")
QQ_GROUP_OPENID = os.environ.get("MEME_GROUP_OPENID", "7861772C9D3065DF0986CAE70EF94435")
QQ_TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"
QQ_API_BASE = "https://api.sgroup.qq.com"
_token_cache = {"token": None, "expires_at": 0.0}


def get_qq_token():
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]
    data = json.dumps({"appId": QQ_APP_ID, "clientSecret": QQ_SECRET}).encode("utf-8")
    req = urllib.request.Request(QQ_TOKEN_URL, data=data,
                                headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        d = json.loads(r.read().decode("utf-8"))
    tok = d.get("access_token")
    if not tok:
        raise RuntimeError("qqbot token failed: %s" % d)
    _token_cache["token"] = tok
    _token_cache["expires_at"] = now + float(d.get("expires_in", 3600))
    return tok


def send_qq_group(text):
    """发文字消息到QQ群，返回是否成功"""
    try:
        token = get_qq_token()
        payload = {
            "content": (text or "")[:4000],
            "msg_type": 0,
            "msg_seq": random.randint(100000, 999999999),
        }
        req = urllib.request.Request(
            f"{QQ_API_BASE}/v2/groups/{QQ_GROUP_OPENID}/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"QQBot {token}", "Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            return r.status == 200
    except Exception as e:
        print("  [QQ推送失败] %s" % str(e)[:80], flush=True)
        return False


# ── 网络层 ──────────────────────────────────────────────

def get(url, retries=3, timeout=20):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            return json.loads(urllib.request.urlopen(req, timeout=timeout, context=ctx).read())
        except Exception as e:
            last = e
            if i < retries - 1:
                time.sleep(2 * (i + 1))
    raise last


def fmt(v):
    v = float(v or 0)
    if v >= 1e9: return "%.2fB" % (v / 1e9)
    if v >= 1e6: return "%.1fM" % (v / 1e6)
    if v >= 1e3: return "%.1fK" % (v / 1e3)
    return "%.4g" % v


def log(evs, push=False):
    """写事件日志，默认不推送。push=True时合并成一条QQ消息发"""
    ts = datetime.datetime.now().strftime("%m-%d %H:%M:%S")
    with open(EVENTS, "a", encoding="utf-8") as f:
        for e in evs:
            f.write(json.dumps({"ts": ts, "event": e}, ensure_ascii=False) + "\n")
            print("%s  %s" % (ts, e), flush=True)
    if push and evs:
        msg = "\n".join(evs)
        if len(msg) > 20:
            send_qq_group(msg)
    return evs


# ── 数据源1: DexScreener ────────────────────────────────

def discover_dexscreener():
    found = set()
    for ep in ["token-boosts/latest/v1", "token-profiles/latest/v1"]:
        try:
            for t in get("https://api.dexscreener.com/%s" % ep):
                if t.get("chainId") == "bsc" and t.get("tokenAddress"):
                    found.add(t["tokenAddress"].lower())
        except Exception as e:
            log(["[DS发现错误] %s: %s" % (ep, str(e)[:60])], push=False)
    return found


def pair_dexscreener(ca):
    try:
        d = get("https://api.dexscreener.com/latest/dex/tokens/%s" % ca)
        pairs = d.get("pairs") or []
        good = [p for p in pairs
                if (p.get("liquidity") or {}).get("usd", 0) >= CFG["min_liq_usd"]
                and p.get("priceUsd") and float(p["priceUsd"]) < 1e6]
        good.sort(key=lambda p: (p.get("liquidity") or {}).get("usd", 0), reverse=True)
        return good[0] if good else None
    except Exception:
        return None


# ── 数据源2: GeckoTerminal ──────────────────────────────

def discover_geckoterminal(max_pages=5):
    found = set()
    for page in range(1, max_pages + 1):
        try:
            d = get("https://api.geckoterminal.com/api/v2/networks/bsc/trending_pools?page=%d" % page,
                    timeout=15)
            pools = d.get("data") or []
            if not pools:
                break
            for p in pools:
                tid = (p.get("relationships", {})
                          .get("base_token", {}).get("data", {}).get("id", ""))
                ca = tid.replace("bsc_", "") if tid else ""
                if ca:
                    found.add(ca.lower())
        except Exception:
            break
        time.sleep(1.5)
    return found


def pair_geckoterminal(ca):
    try:
        d = get("https://api.geckoterminal.com/api/v2/networks/bsc/tokens/%s/pools?page=1" % ca,
                timeout=15)
        pools = d.get("data") or []
        if not pools:
            return None
        pools.sort(key=lambda p: float(p.get("attributes", {}).get("reserve_in_usd") or 0), reverse=True)
        p = pools[0]
        a = p.get("attributes", {})
        chg = a.get("price_change_percentage") or {}
        vol = a.get("volume_usd") or {}
        name = a.get("name", "?")
        symbol = name.split(" / ")[0] if " / " in name else name
        return {
            "symbol": symbol, "priceUsd": a.get("base_token_price_usd", "0"),
            "liquidity": {"usd": float(a.get("reserve_in_usd") or 0)},
            "marketCap": float(a.get("fdv_usd") or 0),
            "priceChange": {"m5": float(chg.get("m5") or 0), "h1": float(chg.get("h1") or 0),
                             "h6": float(chg.get("h6") or 0), "h24": float(chg.get("h24") or 0)},
            "volume": {"m5": float(vol.get("m5") or 0), "h1": float(vol.get("h1") or 0),
                       "h6": float(vol.get("h6") or 0), "h24": float(vol.get("h24") or 0)},
            "pairCreatedAt": _parse_iso_ms(a.get("pool_created_at")),
            "baseToken": {"symbol": symbol, "name": name},
            "_source": "geckoterminal",
        }
    except Exception:
        return None


def _parse_iso_ms(iso_str):
    if not iso_str:
        return 0
    try:
        dt = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except Exception:
        return 0


def get_pair(ca):
    p = pair_dexscreener(ca)
    if p:
        return p
    return pair_geckoterminal(ca)


# ── 盯盘 ────────────────────────────────────────────────

def load_watch():
    if os.path.exists(WATCH):
        try:
            return json.load(open(WATCH, encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_watch(watch):
    json.dump(watch, open(WATCH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def scan_once(watch):
    ts = datetime.datetime.now().strftime("%m-%d %H:%M:%S")

    # ── 1. 发现新热币（双源）──
    discovered = set()
    discovered |= discover_dexscreener()
    discovered |= discover_geckoterminal(max_pages=CFG.get("gecko_pages", 5))

    new_coins = []  # 收集新币，最后合并一条推
    for ca in discovered:
        if ca in watch:
            continue
        p = get_pair(ca)
        if not p:
            continue
        age_h = (time.time() * 1000 - (p.get("pairCreatedAt") or 0)) / 3600000
        sym = p.get("baseToken", {}).get("symbol", ca[:8])
        liq_usd = (p.get("liquidity") or {}).get("usd", 0)
        mcap = p.get("marketCap") or 0

        watch[ca] = {
            "symbol": sym, "source": p.get("_source", "dexscreener"),
            "added": ts, "first_mcap": mcap,
            "last": {"price": float(p.get("priceUsd") or 0), "liq": liq_usd,
                     "vol_m5": (p.get("volume") or {}).get("m5", 0),
                     "vol_h1": (p.get("volume") or {}).get("h1", 0)},
            "last_event": {},
        }

        note = []
        kw = [k for k in CFG["hot_keywords"]
              if k in (sym + p.get("baseToken", {}).get("name", "")).lower()]
        if kw:
            note.append("热词:%s" % ",".join(kw))
        if age_h < 24:
            note.append("池龄%.0f小时" % age_h)
        line = "🆕 [%s] 市值$%s liq$%s %s" % (sym, fmt(mcap), fmt(liq_usd), " ".join(note))
        log([line], push=False)
        new_coins.append(line)

        if len(watch) > CFG["max_watch"]:
            oldest = min(watch, key=lambda k: watch[k]["added"])
            del watch[oldest]

    # 新币只记日志，不推送

    # ── 2. 盯盘池轮询信号 ──
    round_signals = []  # 本轮所有信号，最后合并一条推
    for ca, w in list(watch.items()):
        p = get_pair(ca)
        if not p:
            continue

        sym = w["symbol"]
        now_price = float(p.get("priceUsd") or 0)
        now_liq = (p.get("liquidity") or {}).get("usd", 0)
        now_vol_m5 = (p.get("volume") or {}).get("m5", 0)
        now_vol_h1 = (p.get("volume") or {}).get("h1", 0)
        chg5 = (p.get("priceChange") or {}).get("m5", 0)
        chg1 = (p.get("priceChange") or {}).get("h1", 0)
        mcap = p.get("marketCap") or 0

        old = w.get("last", {})
        last_ev = w.get("last_event", {})
        evs = []
        now_ts = time.time()
        cooldown = CFG.get("event_cooldown_sec", 300)

        if chg5 >= CFG["pump_pct_5m"]:
            ev_key = "pump5"
            if now_ts - last_ev.get(ev_key, 0) > cooldown:
                evs.append("🚀 [%s] 5分钟+%s%% 价$%s\n%s" % (sym, chg5, fmt(now_price), ca))
                last_ev[ev_key] = now_ts

        if chg5 <= CFG["dump_pct_5m"]:
            ev_key = "dump5"
            if now_ts - last_ev.get(ev_key, 0) > cooldown:
                evs.append("🔻 [%s] 5分钟%s%% 价$%s\n%s" % (sym, chg5, fmt(now_price), ca))
                last_ev[ev_key] = now_ts

        if chg1 >= CFG["pump_pct_1h"]:
            ev_key = "pump1h"
            if now_ts - last_ev.get(ev_key, 0) > cooldown:
                evs.append("🔥 [%s] 1小时+%s%% 市值$%s\n%s" % (sym, chg1, fmt(mcap), ca))
                last_ev[ev_key] = now_ts

        if old.get("liq") and old.get("liq", 0) > 0:
            drop = (now_liq - old["liq"]) / old["liq"] * 100
            if drop <= -CFG["liq_drop_pct"]:
                ev_key = "liqdrop"
                if now_ts - last_ev.get(ev_key, 0) > cooldown:
                    evs.append("⚠️ [%s] 流动性-%.0f%% ($%s→$%s) 疑似撤池\n%s" % (
                        sym, -drop, fmt(old["liq"]), fmt(now_liq), ca))
                    last_ev[ev_key] = now_ts

        if old.get("vol_h1") and now_vol_m5 > 2000:
            if now_vol_m5 * 12 > old["vol_h1"] * CFG["vol_spike_ratio"]:
                ev_key = "volspike"
                if now_ts - last_ev.get(ev_key, 0) > cooldown:
                    evs.append("💥 [%s] 5分钟放量$%s 异动\n%s" % (sym, fmt(now_vol_m5), ca))
                    last_ev[ev_key] = now_ts

        if evs:
            log(evs, push=False)
            round_signals.extend(evs)

        w["last"] = {"price": now_price, "liq": now_liq,
                     "vol_m5": now_vol_m5, "vol_h1": now_vol_h1}
        w["last_event"] = last_ev

    save_watch(watch)

    # ── 3. 本轮信号汇总推送（合并一条）──
    if round_signals:
        send_qq_group("🚨 BSC信号报警:\n" + "\n".join(round_signals))


def main():
    loop = "--loop" in sys.argv
    watch = load_watch()
    while True:
        try:
            scan_once(watch)
        except Exception as e:
            log(["[轮次错误] %s" % str(e)[:100]], push=False)
        if not loop:
            break
        time.sleep(CFG["interval_sec"])


if __name__ == "__main__":
    main()
