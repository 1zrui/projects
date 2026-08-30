#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
hermes-bridge 轮询脚本 v2：查 hermes-bridge 仓库的新 Issue/评论（发给本地 Hermes 的消息）。
v2 修复：不再"标记后吞噬"——输出最近 WINDOW_HOURS 小时内创建的消息，
即使上次投递失败，下轮仍能补读，不会永久丢失。
stdout 输出新消息内容（注入 cron LLM prompt）；无新消息输出空 → cron 静默。
"""
import json, subprocess, os, datetime

REPO = "1zrui/hermes-bridge"
WINDOW_HOURS = 2  # 只看最近 2 小时内的消息

def gh(args):
    r = subprocess.run(
        ["gh", "api"] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None

def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(hours=WINDOW_HOURS)
    new_items = []

    issues = gh([f"repos/{REPO}/issues?state=open&per_page=20"]) or []
    for issue in issues:
        if issue.get("pull_request"):
            continue
        iid = issue["number"]
        created = issue.get("created_at", "")
        try:
            ctime = datetime.datetime.fromisoformat(created.replace("Z", "+00:00"))
        except Exception:
            ctime = None
        if ctime and ctime >= cutoff:
            new_items.append({
                "type": "issue",
                "id": iid,
                "author": issue["user"]["login"],
                "title": issue.get("title", ""),
                "body": (issue.get("body") or "")[:3000],
                "created_at": created,
                "url": issue["html_url"],
            })
        comments = gh([f"repos/{REPO}/issues/{iid}/comments?per_page=50"]) or []
        for c in comments:
            ctime_str = c.get("created_at", "")
            try:
                ctime = datetime.datetime.fromisoformat(ctime_str.replace("Z", "+00:00"))
            except Exception:
                ctime = None
            if ctime and ctime >= cutoff:
                new_items.append({
                    "type": "comment",
                    "issue_id": iid,
                    "id": c["id"],
                    "author": c["user"]["login"],
                    "body": (c.get("body") or "")[:3000],
                    "created_at": ctime_str,
                    "url": c["html_url"],
                })

    if not new_items:
        return  # 空 stdout → cron 静默

    print(f"[hermes-bridge] 最近 {WINDOW_HOURS}h 内有 {len(new_items)} 条消息（来自云上 Hermes）:")
    for it in new_items:
        print("=" * 50)
        print(f"类型: {it['type']} | ID: {it.get('id')} | 作者: {it['author']} | 时间: {it.get('created_at')}")
        if it["type"] == "comment":
            print(f"Issue #{it['issue_id']}")
        else:
            print(f"标题: {it['title']}")
        print(f"内容: {it['body']}")
        print(f"链接: {it['url']}")

if __name__ == "__main__":
    main()
