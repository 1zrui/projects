# OpenCode Go 渠道 x-opencode-session 修复

> 摘要：2026-09-06 起 OpenCode Go 上游强制要求 `x-opencode-session` header，new-api 中转层 400；直接改 channels 表 `header_override` 写入固定 session UUID 解决。相关：[[OpenCode Go渠道配置]]、[[OpenCodeGo排行榜抓取修复]]、[[Hermes辅助模型避坑]]

## 问题
2026-09-06 起，OpenCode Go 上游强制要求请求带 `x-opencode-session` header（用于会话路由和 prompt 缓存优化），new-api 中转层默认不带此头，导致所有走 opencode go 渠道的模型（mimo-v2.5、muse-spark-1.3-contributor 等）全部 400 报错：

```
Error from provider (Console Go): Request is missing x-opencode-session and cannot route efficiently.
```

## 根因
- OpenCode Go 官方 9月3日发公告，9月6日强制执行
- 影响所有不自带该 header 的中间层/客户端（new-api、各种 harness 等）
- 参考Issue: https://github.com/charmbracelet/crush/issues/3706

## 修复
new-api 的 channels 表有 `header_override` 字段（JSON格式），直接写入一个固定 session UUID：

```python
import sqlite3, json, uuid
conn = sqlite3.connect('/home/ubuntu/app/new-api/one-api.db')
cur = conn.cursor()
session_id = str(uuid.uuid4())
header_override = json.dumps({'x-opencode-session': session_id})
cur.execute('UPDATE channels SET header_override=? WHERE id=9', (header_override,))
conn.commit()
conn.close()
```

然后重启 new-api：`sudo systemctl restart new-api`

## 验证
```bash
curl -s -X POST "http://127.0.0.1:3000/v1/chat/completions" \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"model":"mimo-v2.5","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'
```

返回正常，修复成功。

## 注意
- `header_override` 写的是 DB 直接改（API 的 PUT 不一定持久化此字段）
- session UUID 是固定的，不是每会话动态生成——够用，OpenCode Go 只要求有这个头即可
- 如果上游后续要求动态 session ID，需改 new-api 代码在请求中间件注入
- new-api 后台界面可能有 header_override 编辑入口，也可以从 UI 改
