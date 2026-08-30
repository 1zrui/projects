---
name: hermes-messaging-platforms
description: "Use when connecting a chat platform (QQ/Weixin) to Hermes."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, gateway, messaging, qq, weixin, dingtalk, feishu, telegram, platform-setup]
    related_skills: [hermes-agent]
---

# Hermes Messaging Platform Setup

How to wire a messaging platform (QQ Bot, Weixin/WeChat, DingTalk, Feishu, Yuanbao, Telegram, …) into a running Hermes gateway. Complements the bundled `hermes-agent` skill: this skill carries the *platform-adapter* detail (config keys, env-var auto-enable, policies, verification) that the hub skill does not.

## When to use

- User asks to 接入/connect/set up a chat platform for Hermes ("接入qq", "connect wechat", "加个钉钉机器人", …).
- A platform is configured but the gateway reports it not connected.
- User needs credentials guidance for an official bot platform (QQ 开放平台, WeCom, Feishu, etc.).

## General workflow

1. **Confirm the adapter exists and find the platform key.**
   - Local install: `ls <HERMES_HOME>/hermes-agent/gateway/platforms/` (per-platform dir or `<name>.py`).
   - Source: `git clone --depth 1 --filter=blob:none --sparse https://github.com/NousResearch/hermes-agent && cd hermes-agent && git sparse-checkout set gateway`.
   - The AUTHORITATIVE platform key is the `Platform` enum in `gateway/config.py` (e.g. `Platform.QQBOT = "qqbot"`). **Do not trust the adapter's docstring config example for the key** — QQ's adapter docstring shows `platforms: qq:` while the real key is `qqbot`. Read `gateway/config.py` for the enum value, the env-var auto-enable block (`getenv("QQ_APP_ID")` etc.), and the "connected" checker (which `extra.*` fields gate startup).
2. **Check runtime dependencies** against the Hermes venv (see Pitfalls for the venv path):
   `python -c "import aiohttp, httpx"` — adapters list deps in the adapter's `check_*_requirements()` function and in `pyproject.toml` extras (most are in the `messaging` extra; aiohttp is nearly universal).
3. **Configure — three paths, in order of preference:**
   - Env vars in `~/.hermes/.env` (secrets only): gateway auto-detects and enables the platform on boot (verified for QQ: `QQ_APP_ID` + `QQ_CLIENT_SECRET`). No config.yaml edit needed.
   - `hermes config set platforms.<key>.enabled true` plus `hermes config set platforms.<key>.extra.<field> <value>` for non-secret knobs. NEVER hand-edit config.yaml (stray indent can corrupt the live gateway).
   - QR scan-to-configure onboard flow, where the adapter ships one (`gateway/platforms/<name>/onboard.py`) — needs the `qrcode` pip package to render.
4. **Restart the gateway** from a SEPARATE shell: `hermes gateway restart` (see Pitfalls re: the security scanner).
5. **Verify**: `hermes gateway status`; also `~/.hermes/gateway_state.json` → `"platforms"` map shows per-platform state. Check `~/.hermes/logs/` on failure.

## Pitfalls

- **QQ C2C 文件接收失败**：`grouptalk.c2c.qq.com` 域名未加入 `url_safety.py` 白名单 + aiohttp `ssl=False` 兼容性问题。详见 `references/qq-file-reception-troubleshooting.md`。补丁在 venv 源码里，`hermes update` 后需重打。
- **Security scanner blocks commands that mention `gateway restart`/`stop` when run inside the gateway process** ("cannot restart or stop the gateway from inside the gateway process"). Even a read-only command whose text contains the phrase can be blocked. Run restarts from a separate shell and avoid embedding the phrase in unrelated compound commands.
- **Hermes venv path is `<HERMES_HOME>/hermes-agent/venv` — NOT `.venv`.** `~/.local/bin/hermes` is a bash shim: `exec "<home>/hermes-agent/venv/bin/hermes" "$@"`.
- GitHub code-search API is rate-limited unauthenticated; sparse clone is the reliable way to read repo internals.
- Default DM/group policy on several platforms (QQ included) is `pairing`: the first message from an unknown user returns a pairing code that must be confirmed before the bot answers normally. Bypass with an `ALLOW_ALL_USERS` env var or tighten with `allow_from` / `<x>_policy` in `extra`.
- New official-platform bots (QQ, WeCom, Feishu) start in **sandbox mode** — they ignore everyone except listed test members until approved/launched. Include this in user-facing steps so the user doesn't report "bot not responding".

## References

- `references/qq-bot.md` — QQ 官方机器人 (QQ Bot API v2) end-to-end setup: open-platform steps, credentials, config keys, policies, STT, verification.
- `references/new-api-relay.md` — New-API 中转站配置：启用对话内容日志、查看 key 使用记录、安全提醒。
