摘要：opencode-go是Hermes保留名会被吞配置，改名opencode-go-via-newapi统一走本地中转站；key必须跟newapi一致否则401；muse-spark-1.3已配好走codex_responses端点。

# OpenCode Go渠道改名与Muse Spark配置

- `providers.opencode-go` 是保留名，配置会被吞，必须改名
- 新名：`opencode-go-via-newapi`
  - `base_url: http://127.0.0.1:3000/v1`
  - `api_mode: codex_responses`（走/v1/responses端点，否则500）
  - `api_key` 必须跟 `providers.newapi` 用同一个，否则报 401 Invalid token
  - `models: ["muse-spark-1.2-contributor", "muse-spark-1.3-contributor"]`
- 2026-09-04 踩坑：改名后直接搬了旧 opencode-go 的专用 key，中转站不认，401。同步成 newapi 的 key + 重启网关解决
- 相关：[[Hermes辅助模型避坑]]、[[OpenCodeGo排行榜抓取修复]]
