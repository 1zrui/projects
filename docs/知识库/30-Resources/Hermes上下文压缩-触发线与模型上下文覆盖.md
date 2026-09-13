# Hermes 上下文压缩：触发线怎么算、模型上下文被低估怎么办

> 摘要：为什么"没聊几句"就弹压缩。触发线 = 模型上下文窗口 × `compression.threshold`。模型上下文窗口由 Hermes 推断，**可能远低于上游真实能力**，需要在 config.yaml 里 `model.context_length` 覆盖。2026-09-11 实测（云上 Hermes + new-api + opencode go）。

## 一、触发公式

```
压缩触发线 = 模型上下文窗口 × compression.threshold
```

当前配置（`~/.hermes/config.yaml`）：

| 配置项 | 值 | 说明 |
|---|---|---|
| `compression.enabled` | true | 开关 |
| `compression.threshold` | **0.5** | 配置值；窗口 <512K 时被 75% floor 抬到 0.75（见 §七.3）|
| `compression.target_ratio` | 0.2 | 压完只保留 20% |
| `compression.model` | mimo-v2.5 | 干压缩活的辅助模型 |
| `compression.protect_first_n` | 3 | 开头 3 条消息不动 |
| `compression.protect_last_n` | 20 | 末尾 20 条消息不动 |
| `model.context_length` | **400000** | 2026-09-11 加的覆盖（原本走内置兜底 128000）|

## 二、模型上下文窗口从哪来（优先级）

1. **顶层 `model.context_length`（config.yaml）—— 优先级最高**（源码注释称 "step 0"，压过 custom_providers 的 per-model 设置）
2. endpoint 专属规则
3. 内置表 `DEFAULT_CONTEXT_LENGTHS`（`agent/model_metadata.py`）
4. models.dev 目录缓存
5. 兜底 `DEFAULT_FALLBACK_CONTEXT`（= CONTEXT_PROBE_TIERS[0]）

**大坑**：内置表有 catch-all 前缀规则：

```
"deepseek": 128000      # agent/model_metadata.py:493
```

这条把 `deepseek-v4.1-flash`、`deepseek-v4-pro` 等全盖成 128k。走自建 new-api 中转时，models.dev 里查不到对应条目，就落到这条 → 128k。

## 三、上游真实能力 vs Hermes 认定（本次实例）

链路：Hermes → new-api(本地:3000) → channel 9「opencode go」`https://opencode.ai/zen/go` → `deepseek-v4.1-flash`

**实测法：查 new-api 的 logs 表，看同一网关历史上成功过的最大 prompt_tokens。**

```sql
select model_name, channel_id, count(*), max(prompt_tokens)
from logs group by model_name order by max(prompt_tokens) desc;
```

结果（channel 9 = opencode go，全部成功返回）：

| 模型 | 成功过的最大 prompt |
|---|---|
| mimo-v2.5 | **533,525** |
| deepseek-v4-flash | 307,221 |
| deepseek-v4-flashgo | 268,780 |
| deepseek-flash | 209,541 |
| muse-spark-1.3-contributor | 191,773 |
| omen-alpha | 190,828 |
| **deepseek-v4.1-flash（当时主模型）** | **98,352** ← 被 128k 认定卡着，从没超过 |

三层对照：

| 层 | 认的上下文 | 依据 |
|---|---|---|
| opencode go 网关（实测） | ≥53 万 | 同网关 mimo-v2.5 跑过 533,525 |
| 模型原生 | 100 万 | DeepSeek 官方 / opencode 目录 |
| models.dev 元数据 | 20 万 | `opencode-go/models/deepseek-v4-flash.toml` 缺 `[limit]` 段，客户端按默认猜 |
| **Hermes（修前）** | **12.8 万** | 内置 catch-all `"deepseek": 128000` |

旁证：opencode 仓库 issue #43272 ——「Go 计划 flash 因 models.dev 缺 limit 字段被卡 200K，**网关本身接受远超 200K**」。

**结论：不是上游小，是 Hermes 猜小了。** 压缩线从 **9.6 万**（128k × 0.75）提到 **30 万**（400k × 0.75）。

## 四、覆盖方法

```yaml
# ~/.hermes/config.yaml
model:
  context_length: 400000      # 顶层，优先级最高
  default: deepseek-flash
  platforms:
    newapi:
      base_url: http://127.0.0.1:3000/v1
      provider: openai
```

或直接 CLI：

```bash
hermes config set model.context_length 400000
```

档位参考：256000（保守）/ **400000（推荐，同网关 53 万有先例）** / 1000000（官方标称）。

**代价提醒**：上下文放大后每次请求带上去的 token 也涨，Go 计划额度有限（社区反馈额度被砍过）。原来 128k 其实是省钱设定。

**注意**：`model.context_length` 是个全局 pin，`/model` 切换模型时若 owner（default 模型 / base_url / provider）变了会被自动清掉（`_clear_persisted_context_for_model_switch`）。

## 五、日志里怎么看

`~/.hermes/logs/agent.log`：

```
Pre-API compression: ~97,336 request tokens >= 96,000 threshold (context=128,000, attempt=1/3)
Preflight compression: ~107,911 tokens >= 96,000 threshold (model deepseek-v4.1-flash, ctx 128,000)
telemetry: main_context_limit: 128000, effective_threshold: 96000, main_model: ..., main_provider: ...
```

压缩遥测关键字段：`main_context_limit`（认定的窗口）、`effective_threshold`（触发线）、`protected_head_tokens` / `protected_tail_tokens`、`middle_window_tokens`、`total_duration_ms`（实测约 57 秒）、`aux_model`。

## 六、三条应对路线

| 方案 | 做法 | 效果 |
|---|---|---|
| 1（推荐）| 覆盖 `model.context_length` 为实测真实值 | 触发线按真实窗口走 |
| 2 | `compression.threshold` 0.5 → 0.75 | 触发线 ×1.5，代价：单次压得更重 |
| 3 | 换大窗口模型 | 治本但受模型选择限制 |

## 七、核验与复现（2026-09-11 实测）

### 1. 函数级核验（最快，不用等日志）

```bash
cd ~/.hermes/hermes-agent && ./venv/bin/python -c "
from agent.model_metadata import get_model_context_length as g
print('裸调           :', g('deepseek-v4.1-flash'))
print('provider=newapi:', g('deepseek-v4.1-flash', provider='newapi'))
print('覆盖 400000    :', g('deepseek-v4.1-flash', config_context_length=400000))
"
```

实测输出：

```
裸调           : 1048576
provider=newapi: 128000      ← 根因就在这一行
覆盖 400000    : 400000
```

**根因精确定位**：带 `provider` 参数（自定义渠道名 newapi / openai）时，模型不在任何已知目录里 → 掉进内置 catch-all `"deepseek": 128000`。**裸调不带 provider 反而能查到 1M**，所以别拿裸调结果判断线上行为。

覆盖逻辑在 `agent/model_metadata.py:2952`：`config_context_length` 有效则最高优先返回。

### 2. 日志核验

```bash
python3 - <<'PY'
import re
for line in open('/home/ubuntu/.hermes/logs/agent.log', errors='ignore'):
    if 'main_context_limit' in line:
        m = re.search(r'main_context_limit"?\s*[:=]\s*"?(\d+)', line)
        t = re.search(r'(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})', line)
        print(t.group(1) if t else '?', m.group(1))
PY
```

**这个字段只在「压缩真的被触发」时才打，不是启动时打。** 改完配置重启网关，日志里不会自动冒出新值 —— 得等新会话真的跑到触发线。所以重启后核不到新值 ≠ 配置没生效。

### 3. 阈值百分比有隐藏 floor（关键）

`context_compressor.py:3047 _effective_threshold_percent`：

```python
_SMALL_CTX_WINDOW_LIMIT      = 512_000   # 窗口小于 512K
_SMALL_CTX_THRESHOLD_PERCENT = 0.75      # 阈值至少 75%
# 显式更大的阈值才赢（如 Codex gpt-5.5 的 85%）；只会抬、不会降
```

窗口 < 512K 时触发线固定为窗口的 75%，**`compression.threshold: 0.5` 被 floor 抬掉**：

| 认定窗口 | 实际触发线 |
|---|---|
| 128,000 | 96,000 |
| **400,000** | **300,000** |
| 1,048,576（≥512K）| 524,288（此时 0.5 才真生效）|

所以"设 40 万 → 20 万触发线"是错的，实际是 **30 万**。

### 4. 要不要直接上 1M

| 选项 | 触发线 | 评价 |
|---|---|---|
| 400,000 | 30 万 | 推荐，够用且省额度 |
| 1,048,576 | 52 万 | 单次请求 token 暴涨，Go 计划额度未知 |

先跑 40 万观察。此外注意：当前**已在跑的会话**仍带旧缓存值，**要新会话才吃到新值**。

## 八、踩坑记录

- **重启网关不能在网关进程内做**：`systemctl --user restart hermes-gateway` 会被拦截（SIGTERM 会传播杀掉命令自身）。要么从外部 shell 跑 `hermes gateway restart`，要么用延迟脱离方式（`(sleep 30; echo <base64> | base64 -d | bash) &`）让当前回复先送出。
- `hermes config set model.context_length 400000` 会写成 int，YAML 校验正常。
- 别对整个安装目录 `grep -r`，会扫进 node_modules 炸输出；限定 `agent/`、`hermes_cli/`。
- `state.db` 的 `sessions` 表列名不是 `session_id`，查前先 `PRAGMA table_info`。
- new-api 的 `logs` 表模型列名是 **`model_name`**，不是 `model`。
- 压缩跟"用户说了几句话"无关；工具输出（API 原始返回、文件内容、脚本）才是吃 token 的大头。
- 上游 opencode zen 的 `/v1/models` 只返回模型 id，**不含 context 元数据**；想知道真实上限只能靠上述 logs 实测法。
