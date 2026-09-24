# Hermes 内置生图能力 + artflow 接入方案（2026-09-24 实测）

## 结论：有，Hermes 内置 `image_generate` 工具

- **工具名**：`image_generate`，toolsets.py 里属于 **`image_gen`** toolset
  （本机 `~/.hermes/config.yaml` 的 enabled toolsets 里**已经列出 `image_gen`**）
- **工具只有在某个后端 `is_available()` 为 True 时才会真正注册** —— 本机 8 个后端
  **一个都没配 key**，所以 `tool_search` 里搜不到 `image_generate`。
- **官方文档**：https://hermes-agent.nousresearch.com/docs/user-guide/features/image-generation
- **插件开发文档**：https://hermes-agent.nousresearch.com/docs/developer-guide/image-gen-provider-plugin

## 内置的 8 个生图后端（`~/.hermes/hermes-agent/plugins/image_gen/`）

| 后端 | 模型 | 需要的 key | 备注 |
|---|---|---|---|
| `fal` | flux-2-klein/pro、nano-banana-2/pro、gpt-image-1.5、recraft-v3 | `FAL_KEY` | 官方文档首选 |
| **`openai`** | **GPT Image 2 / 2.5 Flare / 2.5 Sunburst** | `OPENAI_API_KEY` | **★ 与 artflow 提供的模型完全一致** |
| `openai-codex` | gpt-image-2 | 无（走 ChatGPT/Codex OAuth） | 有 Codex 订阅就能用 |
| `openrouter` | gpt-image-2、Krea 2、Qwen Image 3 Pro、MAI-Image-2.5、Grok Imagine | `OPENROUTER_API_KEY` | 支持最多 16 张参考图、文生图+图生图 |
| `deepinfra` | FLUX、Qwen-Image 等 | `DEEPINFRA_API_KEY` | 目录从 API 实时拉 |
| `krea` | Krea 2 Large/Medium/Turbo | `KREA_API_KEY` 或 Nous 订阅网关 | 异步 job + 轮询 |
| `meta-ai` | muse-image | `META_MODEL_API_KEY` | 存到 `$HERMES_HOME/cache/images/` |
| `xai` | grok-imagine-image | xAI 凭据 | 仅文生图 |

**另外**：Nous Portal 订阅（`docs/user-guide/features/tool-gateway`）能一个订阅打通全部工具，
包括 image generation，无需额外 API key。

## ★★ 走自建 new-api（推荐，2026-09-24 实测跑通）

大哥已把 artflow 配进自建 new-api，**渠道 39「image」**：
- base_url `https://api.artflow.vip`
- models `gpt-image-2.5-flare`, `gpt-image-2.5-sunburst`
- status 启用

**为什么走 new-api 而不是直连 artflow**：实测 **39.4s vs 163.8s**，快 4 倍
（new-api 有连接复用/中转优化）。另外 key 和配额统一在 new-api 管理。

**要设的环境变量（`~/.hermes/.env`）**：
```bash
OPENAI_API_KEY=<new-api 的 token>        # 从 /home/ubuntu/app/new-api/one-api.db 的 tokens 表取
OPENAI_BASE_URL=http://127.0.0.1:3000/v1  # 自建 new-api
OPENAI_IMAGE_MODEL=gpt-image-2.5-flare    # 必须设，否则默认 gpt-image-2 会 403
```

**实测（2026-09-24）**：
```
is_available(): True
耗时 39.4s
success: True
image: ~/.hermes/cache/images/openai_gpt-image-2.5-flare_20260924_172640_4463700d.png
```

**new-api 侧的验证（同样实测通过）**：
```
POST http://127.0.0.1:3000/v1/images/generations
{"model":"gpt-image-2.5-flare", ...} → HTTP 200 | 211.8s | 返回 url
```
（new-api `/v1/models` 共 36 个模型，生图相关 3 个：
`gpt-image-2.5-flare` / `gpt-image-2.5-sunburst` / `agnes-image-2.5-flash`）

**⛔ 不要配 `agnes-image-2.5-flash`（渠道 32-38「Agens」）** —— 大哥 2026-09-24 明确指示。
（虽然它只要 7.7s，很快。）

## ✅ 已配置（2026-09-24 完成）

`~/.hermes/.env` 末尾已追加（备份：`~/.hermes/.env.bak-before-imagegen-*`）：
```bash
# ---- Hermes 内置生图 (image_generate) → 自建 new-api → artflow (2026-09-24) ----
OPENAI_API_KEY=sk-F6sw...zRrY      # 复用 providers.newapi 的 admin token
OPENAI_BASE_URL=http://127.0.0.1:3000/v1
OPENAI_IMAGE_MODEL=gpt-image-2.5-flare
```

**验证（load_hermes_dotenv + get_secret，实测通过）**：
```
OPENAI_API_KEY 读到: sk-F6swV9q...zRrY
OPENAI_BASE_URL: http://127.0.0.1:3000/v1
OPENAI_IMAGE_MODEL: gpt-image-2.5-flare
is_available(): True
解析模型: gpt-image-2.5-flare -> api_model = gpt-image-2.5-flare
```

**⚠️ 改完 `.env` 必须重启网关** `image_generate` 工具才会注册进工具列表
（会话中途改 env 不会热加载工具集）：QQ 里发 `/restart`。

### ⚠️ 光配 env 还不够：必须设 `image_gen.provider`（2026-09-24 踩坑）

重启后 8 个 provider 都注册了，但工具仍然不出现，日志报：
```
WARNING tools.registry: check_fn check_image_generation_requirements returned False;
dependent tools will be unavailable this turn
```

**根因**（`tools/image_generation_tool.py`）：
```python
def check_image_generation_requirements() -> bool:
    if check_fal_api_key(): ...            # 没配 FAL_KEY → 跳过
    configured = _plugin_provider_name()   # 读 image_gen.provider
    if configured is None:
        return False                       # ← 这里挂掉
    provider = _get_plugin_provider(configured)
    return bool(provider and provider.is_available())
```
`_plugin_provider_name()` 的逻辑是"**没有显式配置就返回 None**"——设计意图是
「用户可能只为别的功能设了 OPENAI_API_KEY，不该因此自动接入付费生图后端」。
所以**必须显式声明用哪个后端**：

```bash
hermes config set image_gen.provider openai
```
（CLI 会警告 `'image_gen.provider' is not a recognized config key` —— **是误报**。
`_read_image_gen_key()` 读的就是 `config.yaml` 的 `image_gen.<key>`，代码确实生效。）

**验证（独立进程，实测通过）**：
```
_plugin_provider_name(): openai
provider.is_available(): True
check_image_generation_requirements(): True    # ← 设之前是 False
```

**所以完整配置是三处**：`.env` 三个变量 + `config.yaml` 的 `image_gen.provider`，
**然后必须重启网关**。

## ✅ 端到端跑通（2026-09-24 17:37）

重启后 `image_generate` 工具正式出现在工具列表里，实测出图成功：
```
image: ~/.hermes/cache/images/openai_gpt-image-2.5-flare_20260924_173729_52afbcfc.png
model: gpt-image-2.5-flare | size: 1024x1024 | quality: auto | provider: openai
```
提示词（中文）：「一只橘猫坐在木质窗台上，午后阳光斜射进来形成温暖的光柱，浅景深，
背景是虚化的绿植，电影级摄影质感，细节丰富」—— 中文提示词正常，`revised_prompt` 原样回传。

**工具参数**（`image_generate`）：
- `prompt`（必需）
- `aspect_ratio`：`landscape`(16:9) / `square`(1:1) / `portrait`(竖)
- `image_url`：传源图则走 `images.edit`（图生图/编辑）
- `reference_image_urls`：最多 16 张参考图（风格/人物/构图）

**排障口诀**：工具不出现 → 先看日志有没有
`check_fn check_image_generation_requirements returned False`。
有 → 缺的是 **`image_gen.provider`**（不是 env）；
没有这条警告 = 检查已通过，工具应已注册。

**取数备忘**：new-api 的 token 在 `/home/ubuntu/app/new-api/one-api.db` 的 `tokens` 表
（`SELECT key FROM tokens`）；Hermes 自己用的是 `sk-F6swV9qh...` 那个 admin token，
与 `config.yaml` 的 `providers.newapi.api_key` 是同一个。

## ★ 直连 artflow（备选，不推荐）

**原理**：`plugins/image_gen/openai/__init__.py` 里是
```python
client = openai.OpenAI(api_key=api_key)   # 没传 base_url
```
OpenAI SDK **会读环境变量 `OPENAI_BASE_URL`** —— 所以把它指向 artflow，
内置 `image_generate` 工具就直接走 artflow 了，**一行代码都不用改**。

**要设的三个环境变量（`~/.hermes/.env`）**：
```bash
OPENAI_API_KEY=sk-...（artflow 的 key，已存 ~/.config/artflow/key）
OPENAI_BASE_URL=https://api.artflow.vip/v1
OPENAI_IMAGE_MODEL=gpt-image-2.5-flare
```
第三项**必须设** —— 插件默认模型是 `gpt-image-2-medium`，artflow 上没有这个模型，
不设会报 `403 This token has no access to model gpt-image-2`。

**内置插件原生支持的 model key（15 档）**：
```
gpt-image-2-{low,medium,high}
gpt-image-2.5-flare{,-low,-medium,-high,-xhigh,-max}
gpt-image-2.5-sunburst{,-low,-medium,-high,-xhigh,-max}
```

**实测（2026-09-24）**：
```
is_available(): True
耗时 163.8s
success: True
image: ~/.hermes/cache/images/openai_gpt-image-2.5-flare_20260924_171646_5978f4f9.png
model: gpt-image-2.5-flare
```

**⚠️ 副作用（配之前必须知道）**：`OPENAI_BASE_URL` 是**全局环境变量**，会影响
所有读它的组件。grep 全仓结果：只有 `plugins/memory/mem0/_openai_llm.py` 和
`_oss_providers.py` 会读它（mem0 记忆后端）。**没用 mem0 就安全**；
用了 mem0 要确认它的 embedding/LLM 调用不会被带偏。
（`tools/tts_tool_openai.py` 走的是 config 里的 `openai.base_url`，不读 env，不受影响。）

**替代方案（不动全局 env）**：用 `hermes tools` → Image Generation → OpenAI 配置，
或改用 `image_gen.openai.model` config 键指定模型；但 base_url 这一项目前只能靠
env（插件没暴露 base_url 配置键）。

## 相关
- [[artflow生图API-测试报告-2026-09-24]]
- 本机已有生图通道：doubao-image-gen（豆包，CDP 驱动）、ComfyUI
