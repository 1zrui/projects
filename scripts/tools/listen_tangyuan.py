#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""监听群里汤圆(2242413547)的新回复，发现即输出并退出。
用法: python listen_tangyuan.py [last_seen_message_id]
"""
import sys, time, json, urllib.request

GROUP_ID = 1064105365
TANGYUAN_QQ = "2242413547"
API = "http://127.0.0.1:18801/get_group_msg_history"
POLL_INTERVAL = 6  # 秒（大哥指定）
MAX_WAIT = 600     # 秒（10分钟上限，超时退出）

def fetch_history():
    data = json.dumps({"group_id": GROUP_ID, "message_seq": 0, "count": 10}).encode("utf-8")
    req = urllib.request.Request(API, data=data, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode("utf-8")).get("data", {}).get("messages", [])
    except Exception as e:
        return []

def main():
    start = time.time()
    baseline = None  # 启动时汤圆最新消息的 time 时间戳，只响应比它新的

    # 先取当前汤圆最新消息 time 作为基线（QQ message_id 不按时间递增，必须用 time）
    # 注意：history 返回顺序不保证最新在前，要取所有汤圆消息中 time 最大值
    for m in fetch_history():
        if str(m.get("user_id", "")) == TANGYUAN_QQ:
            t = m.get("time")
            if t is not None and (baseline is None or t > baseline):
                baseline = t

    while time.time() - start < MAX_WAIT:
        msgs = fetch_history()
        # 找汤圆的最新消息
        for m in msgs:
            uid = str(m.get("user_id", ""))
            if uid == TANGYUAN_QQ:
                t = m.get("time")
                if baseline is not None and t is not None and t > baseline:
                    # 提取文本
                    segs = m.get("message", [])
                    text = ""
                    if isinstance(segs, str):
                        text = segs
                    else:
                        parts = []
                        for s in segs:
                            if s.get("type") == "text":
                                parts.append(s.get("data", {}).get("text", ""))
                            elif s.get("type") == "at":
                                parts.append("[at:" + str(s.get("data", {}).get("qq", "")) + "]")
                        text = "".join(parts)
                    print("TANGYUAN_REPLY:" + json.dumps({"message_id": m.get("message_id"), "time": t, "text": text}, ensure_ascii=False))
                    return 0
        time.sleep(POLL_INTERVAL)
    print("NO_REPLY_TIMEOUT")
    return 1

if __name__ == "__main__":
    sys.exit(main())
