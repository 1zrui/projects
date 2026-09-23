# Jev (TypeSafe AI) 决策模型调研 — 2026-09-22

摘要：Jev 是 TypeSafe AI 2026-09-15 发布的"System One"决策模型，不生成文字，只对预定义问题并行返回类型化答案+校准概率。快 5~25 倍、便宜 400 倍是真的；"前沿智能"是吹的，且大陆未开放、中文偏弱。

## 一句话结论
不是"更聪明的模型"，是"更快更便宜的判断器"。适合 Agent 里的分类/路由/打分/护栏，不适合生成、推理和任何接资金的场景。

## 基本盘
- 出品：TypeSafe AI，创始人 Diogo Almeida（前 OpenAI，InstructGPT/RLHF 核心作者），2026-09-15 发布，早期访问制，DCVC 领投 4000 万美元种子轮，估值约 2 亿。
- 名字：卡尼曼 System 1（快、直觉）+ 杰文斯悖论（单次成本降一个数量级，总用量涨几个数量级）。
- 架构：非自回归。跳过逐 token 解码，把概率分布直接长在答案字段上，一次前向并行算出所有问题。
- 训练：RLCD（Reinforcement Learning for Calibrated Decisions），优化"概率是否诚实"而非人类偏好。

## 三种问题原语
| 原语 | 返回 | 用途 |
|---|---|---|
| Choice | 从 ≤255 个选项选一 + 全选项概率分布 | 分类、路由、意图识别 |
| Score | 有序量表上打分（可 1.6 这种小数） | 风险分级、情绪、排序 |
| Noul | 0~1 单一概率，是/否命题 | 二次校验、分支、护栏 |

要点：问题之间并行独立，一次全问掉几乎不增延迟（只多花输入 token）。官方反直觉建议——不要写连环推理，拆成原子问题。

## 价格与速度
- 输入 $0.042/百万 token，输出免费。
- 官方：端到端 70~500ms，比大模型快 193.6 倍、便宜 444.6 倍。
- 实测（第三方审计）：快 5~25 倍、海外端到端 1.6~3.7 秒（官方数字是美西本机跑的）。国内只会更差。
- 工作流评测：Jev 67.8% / $0.0004 / 0.4s vs GPT-5.6 Terra 约 68% / $0.03 / 10s vs Opus 5 73% / $0.18 / 38s。

**已安装（2026-09-22）**：插件复制到 `~/.hermes/hermes-agent/plugins/context_engine/jev_prune/`，
`context.engine` 已设为 `jev_prune`。加载器复验通过（`discover_context_engines` 可见，`is_available=True`）。

```bash
# 回退
hermes config set context.engine compressor
```

**加载器的硬坑**：`plugin_loader.instance_from_module` 用**无参实例化**探测引擎
（`attr()`），而 `ContextCompressor.__init__` 第一个参数 `model` 是必填 ——
不加兼容 `__init__` 就会静默返回 None，只留一句 `loaded but no engine instance found`。
插件里必须写 `def __init__(self, model: str = "", **kwargs)`，真实模型由 host 之后
通过 `update_model(model, context_length, ...)` 传入。

**生效条件**：`context.engine` 是 init 时选的，**必须重启网关**（QQ 里发 `/restart`）或开新会话。

### 参数定值依据（不是拍的）

| 项 | 值 | 依据 |
|---|---|---|
| `threshold_tokens` | 300,000 | 400,000 × 0.75（窗口 <512K 时阈值被 floor 抬到 75%） |
| `jev_trigger_ratio` | 0.62 → 触发线 **186,000** | 在完整压缩（30 万、实测 57s）之前留 11 万缓冲 |
| `jev_min_regrowth` | 60,000 | 剪完必须涨这么多才允许再剪 —— `prune_tool_results_only` 在工具循环里**每轮都被调用**，没有滞后门会每轮改写历史、打穿提示词缓存 |
| `jev_max_judgements` / `jev_min_interval` | 15 条 / 2.0s | 单次最坏 30s，**必须比一次完整压缩（57s）快**，否则本末倒置 |
| `jev_min_chars` | 4000 | 大块才是 token 大头，小块不值得花调用 |
| `proactive_prune_tokens` | **保持 0** | 内置剪枝与 Jev 剪枝都会改写历史 → 同时开等于双重破坏缓存。先用 Jev 观察一轮，不够再开内置兜底 |

**端到端验证结果**（真实 dump + 真实 Jev API）：296 条 / 441,667 字符 → 候选 36 条；
剪 6 条省 126,762 字符 ≈ 42,254 token（21.3s）；同 token 再调被滞后门挡住（0 条）；
token 涨过滞后门后恢复可剪。剪后消息形如 `[Jev 判定为噪音，已剪除：14,133 字符]`。

**重启前实测（模拟 host 完整初始化流程）**：
```
选中引擎: JevPruneEngine
threshold_tokens = 300,000
WARNING plugins.context_engine.jev_prune: JevPruneEngine ACTIVE |
        model=deepseek-v4.1-flash context=400000 threshold=300000 jev_trigger=186000 regrowth=60000
```

**自检日志放 `update_model` 而不是 `__init__`**：加载器探测用无参占位实例，
`__init__` 里看到的是 `jev-prune-pending` / 256k 这些假值；host 之后调
`update_model(model, context_length)` 才是线上真实参数。

**排查坑**：日志里 `Using context engine: <name>` 会被 `agent.quiet_mode` 压掉，
加载失败时也没有明显 warning → 光看日志判断不了引擎有没有接管。
要确证就在引擎里加 warning 级别的自检日志，或直接跑
`_select_context_engine({"context": {"engine": "<name>"}})` 看返回类型。

**顺带发现**：`model.context_length` 又没了（原本 400,000）。翻了全部 11 个
配置备份，**包括动手前的自动备份，全都是 None** —— 说明这个全局 pin 在那之前
就被清掉了（`/model` 切模型时 owner 变了会自动清）。已重新 `hermes config set
model.context_length 400000`，压缩线回到 300,000。

### ⚠️ 上线后发现的真 bug：滞后门把剪枝锁死了（2026-09-22 修复）

第一版插件用了"剪完抬门槛"的滞后门（`_jev_rearm_tokens = 剪后估算 + 60k`），
理由是防止每轮改写历史打穿提示词缓存。**但这是错的**：

- 插件**不写回会话数据库**（内置的会调 `session_db.archive_and_compact`，本插件没调）。
- 所以 host 每次请求都从库里用**完整**历史重建 messages。
- 而滞后门是按"剪后估算值"设的 → 第二次请求直接被挡住 → **上下文反弹回原样**。
- 症状：日志里 `jev_prune: dropped N` **只出现一次**，之后再无痕迹；
  数据库里查不到任何被剪的工具消息（`role='tool' AND content LIKE '[Jev 判定为噪音%'` 命中 0 条）。

**正确解法：按内容哈希缓存判定结果**，去掉滞后门。
每轮都剪（上下文始终是小的），但同样的内容直接命中缓存、不重复调 Jev：

```python
self._jev_verdicts: dict[str, tuple[float, float]] = {}   # sha1(content)[:16] -> (noise, useful)
```

`_should_run` 也必须用 `max(current_tokens, Σ messages 估算)` ——
`current_tokens` 可能是上一次请求（已剪）的读数，只用它同样会漏剪。

**修复后实测**：第 1 次剪 13 条 / 40.2s / 省 166,717 字符；第 2、3 次均 **0.01s**
（缓存命中），三次结果完全一致。

### ⚠️ 第二次修复：内存缓存跨调用没保持 → 改落盘（2026-09-22）

上线后日志显示**连续两次剪枝都是全量新判**（`newly judged 15` / `newly judged 10`，
零缓存命中），等于每轮都重烧 40s。

根因：本插件**不写回会话数据库**，host 每次请求都用完整历史重建 messages；
而**内存缓存没能在两次调用之间保持**（实例状态在请求间被重建/重置）。

**修法：判定缓存落盘到 `$HERMES_HOME/jev_prune_cache.json`**（原子写：`.tmp` + `replace`）。
key = `sha1(content)[:16]`，value = `[noise, useful]`，上限 5000 条。

**跨进程验证**：
```
进程 A（缓存空）: 启动 0 条  → 剪 10 条 / 32.62s / 缓存 12 条
进程 B（新进程）: 启动 12 条 → 剪 10 条 / 0.01s   ← 磁盘命中
```

**为什么不用内置那条落库路径**：`session_db.archive_and_compact` 牵扯
transcript 写入准入检查、`compression_locks`、水位线提交、`session_turn_leases` ——
插件直接调风险太高，宁可自己维护一份只读的判定缓存。

**日志公式坑**：`dropped - judged` 不等于"缓存命中数"（前者含缓存命中的剪枝），
会打出负数。必须单独计数 `cached_hits`。

**排查坑**：用 `content LIKE '%Jev 判定为噪音%'` 查库会把 assistant 消息里
引用过的示例文本也算进去（出现多个相同的假数字）。必须加 `role='tool'`
且用前缀匹配 `content LIKE '[Jev 判定为噪音%'`。

### ⚠️⚠️ 第三次修复（最关键）：钩子挂错了位置，Jev 根本没被调用（2026-09-23）

上线后 Jev 一次都没跑过。日志真相：

```
14:26:06  context compression started: messages=280 tokens=~317,642
14:26:06  Pre-compression: pruned 124 old tool result(s)
14:26:06  Context compression triggered (317642 >= 300000 threshold)
14:27:55  Compressed: 280 -> 29 messages (~128,822 tokens saved, 83%)
```

**根因：`agent/turn_preflight.py` 的压缩分支结构**

```python
if (agent.compression_enabled
    and compression_attempts < max_compression_attempts
    and _compressor.should_compress(_real_tokens)):     # ← True 就直接压缩
    ...走完整压缩（LLM 摘要）...
elif agent.compression_enabled:                          # ← 只有上面 False 才轮到
    _prune(messages, current_tokens=_real_tokens)        # ← prune_tool_results_only
```

推论（三条都实测过）：
1. **`prune_tool_results_only` 只在 `should_compress()` 返回 False 时才被调用。**
   本插件自己定的 `jev_trigger_ratio` 阈值 host 根本不读 —— 光调低它没有任何作用。
2. **要让 Jev 上场，必须重写 `should_compress_info()`**：在"Jev 还能剪"时返回
   `(False, "jev_prune_first")`，把 host 让进 `elif` 分支。这是唯一正确的钩子位置。
3. **`proactive_prune_tokens <= 0` 会让内置剪枝第一句就 return**（no-op）。
   本插件是 super() 之后再叠 Jev，所以那层失效不影响自己，但别指望内置兜底。

**兜底设计（防 Jev 无限推迟压缩把上下文顶爆窗口）**
- `_jev_dry`：上一轮 Jev 一条都没剪动 → 下次放行压缩。**放行时必须置回 False**，
  否则走 `if` 分支后再没人重置它，之后每轮都直接压缩、Jev 永远失业。
- `_jev_dry` **只在"真的跑过判定"时更新**：上下文没到触发线时 Jev 压根没跑，
  这时置 dry 会让下次刚超阈值就直奔压缩（`_jev_prune` 因此返回 `(msgs, dropped, ran)`）。
- `jev_hard_ratio = 1.15`：prompt ≥ 阈值×1.15 直接放行压缩（阈值 30 万 → 34.5 万）。

**验证矩阵（全部实测通过）**
```
prompt= 50,000 → 压缩=False (super 本就不该压)   Jev 未跑, _jev_dry 未被污染
prompt=200,000 → 压缩=False (super)              剪 13 条
prompt=330,000 → 压缩=False jev_prune_first      ← 推迟给 Jev
prompt=360,000 → 压缩=True                       ← 硬保护放行
同内容再跑     → 0.008s（缓存命中）
```

## 交付物：CLI 工具 + Hermes 插件（2026-09-22）

路径 `~/workspace/jev/`：
- `jev.py` —— 命令行工具，`noul`（是/否）/ `ask`（一次多问）/ `prune`（剪枝会话 dump）。key 读 `$TYPESAFE_API_KEY` 或 `~/.config/typesafe/key`；内置 3.2s 最小间隔 + 429 退避。
- `plugin/jev_prune/` —— Hermes context engine 插件，**继承内置 `ContextCompressor`**，只覆盖 `prune_tool_results_only`，在确定性剪枝之上叠加 Jev 噪音判定。Jev 挂了就静默回退。
- `README.md` —— 用法 + 三条设计铁律 + 实测数据。

插件安装（未执行，待确认）：
```bash
cp -r ~/workspace/jev/plugin/jev_prune ~/.hermes/hermes-agent/plugins/context_engine/
hermes config set context.engine jev_prune   # 重启网关生效
```

**重要发现：Hermes 内置的剪枝是关着的。** `compression.proactive_prune_tokens: 0` = 关闭。
内置 `_prune_old_tool_results` 做四件事且**零 LLM 调用、零成本**：
(1) 去重字节相同的工具结果（无损，保留最新完整副本 + 反向引用）；
(2) 摘要非尾部、大于 `proactive_prune_min_result_chars` 的工具结果；
(3) 截断超大 tool_call 参数；
(3.5) 退休旧图片载荷。
并且**自带提示词缓存滞后保护**（`proactive_prune_min_reclaim_tokens` + regrowth runway）。
→ 结论：**先开内置的拿基础收益，再叠 Jev 做更准的判断**，顺序不能反。

## 上下文压缩实测：省 token 是真的，但省的原因值得看清楚（2026-09-22）

### 我的实测（本机真实 Hermes 会话 dump）
- 样本：296 消息 / 18.3 万 token，**工具输出 107 条占 78%**（最大一条 8.5 万字符 ≈ 2.8 万 token）
- 做法：Jev 逐条判，state = 任务背景 + 该条输出 head 1800 / tail 400 字符
- 结果：83 条判定完成 → **可剪 53 条 = 304,387 字符 ≈ 10.1 万 token，可压缩 82%**
- 判断**有区分度**：滚动日志 useful 0.06~0.15 / noise 0.7~0.9 → 剪；小段关键输出 useful 0.81~0.88 → 留

### 社区回放数据（GitHub `tamaratran/fast-jev-compaction` issue #26）
- 16 个 Claude Code 会话、2 个项目、8 个压缩点、277 工具调用（21 pinned，256 评分），8 次请求 / 134,074 输入 token / 均 877ms
- 字符减少 **87.7%**，丢弃或截断 240 条
- **对照"对所有问题都答 0 的假模型"：88.5% 减少、244 条丢弃 —— 几乎一模一样**

| | 真实 Jev | 假 asker（全答 0） |
|---|---|---|
| 字符减少 | 87.7% | 88.5% |
| 丢弃/截断 | 240 | 244 |
| 其中后来又被用到 | 16 (6.7%) | 16 (6.6%) |

**根因**：插件 state 里每条工具结果只写 `ok, 4213 chars (omitted)`，Jev 只看到工具名+参数+长度，**看不到内容**；`STATE_CONTEXT` 又告诉它"可以随时重跑工具/重读文件"，于是 256 个 result 评分**没有一个 ≥ 0.5**（直方图 max < 0.3）。
→ **87.7% 的节省来自"删掉所有非 pinned 工具结果"这个策略本身，Jev 的智能判断几乎没贡献。** 对比我自己的实测（给了 head+tail 内容）才有区分度 —— 差别就在这。

**代价**：丢弃的 240 条里 16 条（6.7%）后来又被用到（15 条是 Bash 输出）。
**相关 bug**：demo 里 Jev 给 `Edit` 调用打 0.36 丢掉，但同文件早前的 `Read` 保留 → 历史显示编辑前的文件，无变更痕迹。

### 正确配置（issue 作者提案 + 我的实测验证）
1. **state 里给每条结果塞 head + tail 各约 200 字符**，让评分有依据（不给内容 = 等于随机删）
2. **加规则保护，不问 Jev 直接保留**：失败调用、`Agent`/`Task`/`AskUserQuestion` 结果、`Edit`/`Write`、编辑前最新的 `Read`
3. 用**任务成功率 + 完成任务的 token 总量**评估，不要只看压缩率
4. 注意提示词缓存：删历史中段会让后面全部重写缓存（cache write 可占总开销 60%+），优先删**尾部之前的大块噪音**而不是到处打洞

**caveat**：issue 只有 8 个点/2 项目/1 用户，且会话多为中文（官方称 CJK 准确率更低）。

**限流实测**：Vercel 免费层每模型有限速 —— 连续 30+ 次请求触发 429。按 `retry-after` 退避、每次间隔 3.2s 可稳定跑完 83 条（202s）。想接进 agent 循环高频调用，免费层顶不住。

## 实测结果（2026-09-22，绑卡后，服务器走代理）

绑卡后**同一个 key 立刻可用**，`cost: "0"`（免费层，marketCost 约 $0.00002/次）。

| 场景 | 延迟 | 结果 |
|---|---|---|
| 客服工单（紧急+部门+情绪，一次 3 问） | 1.64s | urgent 0.98；department=logistics 0.84；anger 1.04 |
| 垃圾评论审核（是否垃圾+类别+风险） | 0.79s | is_spam 0.98；category=fraud 0.60 / ad 0.40（confidence **0.46**）；risk 1.99 |
| Agent 模型路由（复杂度+是否要代码+能否用便宜模型） | 0.60s | complexity=medium 0.99；needs_code 0.96；can_be_cheap 0.39 |

**稳定性（同一中文输入连跑 5 次）**：urgent 0.930/0.930/0.930/0.940/0.940（漂移 **0.010**），sentiment 五次全等 1.020（漂移 **0**）。延迟中位 **0.60s**（0.57~0.69s）。

**判断**：中文场景可用，结论都合理。模糊案例会主动给低 confidence（fraud 0.6 vs ad 0.4 → confidence 0.46），校准行为符合宣传，不是硬编一个答案。0.6s 延迟是走代理绕行的结果（官方美西本机 70-500ms），完全够用。

**调用要点**：Vercel 版 questions 类型用 `boolean`（官方原生 API 用 `noul`）；一次问 3~10 个问题延迟几乎不变，输入 token 约 400~500/次。key 存 `~/.config/typesafe/key`（chmod 600）。

## 获取途径（2026-09-22 实测）

### ⚠️ 实测踩坑：Vercel 免费层必须绑信用卡才能用（2026-09-22 验证）
拿真实 key（`vcp_` 前缀，60 字符）实测，**认证通过但被拒**：

```
POST https://ai-gateway.vercel.sh/v1/evaluate
HTTP 403
{"error":{"message":"AI Gateway requires a valid credit card on file to service requests.
Please visit https://vercel.com/d?to=%2F%5Bteam%5D%2F%7E%2Fai%3Fmodal%3Dadd-credit-card
to add a card and unlock your free credits.","type":"customer_verification_required"}}
```

换 `xiaomi/mimo-v2.6-flash`（同为免费层文本模型）也是同样的 403，说明**不是 Jev 的问题，是账号级门槛**。

- 官方文档原话：*"You need a Vercel account and a team with a **valid payment method**, which unlocks free AI Gateway Credits."*
- 后果：**不绑卡，AI Gateway 任何模型都调不动**，连建 key 都可能在前端报 "Something went wrong / There was an issue displaying the content"。
- 绑卡入口：`https://vercel.com/d?to=%2F%5Bteam%5D%2F%7E%2Fai%3Fmodal%3Dadd-credit-card`
- 绑卡不等于扣钱：免费层 $5/月，Jev $0.042/M 输入 → 够跑约 1.19 亿输入 token。
- Vercel 状态页当时全绿，报错与平台故障无关。

### 备选：本地跑开源复现（不用卡）
- APUS `fast-browser-use`（MIT，2026-09-19 开源）：单 token logits 快速决策 + KV-Cache 广播，本地 Qwen3.5-9B 做决策。
- 门槛：M2 Pro 级消费硬件。**云服务器 4 核 3G 无 GPU 跑不了 9B**，最多跑 0.6B 级（B 站有人演示），效果远不及原版。
- 结论：想要原版质量，绕不开绑卡；不绑卡只能自降规格。

### 结论：Vercel 免费层就能白嫖
`typesafe-ai/jev` 已确认在 Vercel AI Gateway 的**免费层模型列表**里（`Free Tier: Yes`，筛选页 /ai-gateway/models?freeTier=true 可见）。Vercel 免费层每月 $5 额度，Jev 输入 $0.042/M 且输出不计费 → $5 够跑约 1.19 亿输入 token，个人用途根本用不完。

**Vercel 拿 key 步骤**
1. vercel.com/signup，用 GitHub 一键登录（或 Email/Google/ChatGPT）
2. Dashboard → AI Gateway → API Keys → Create
3. 得到 `AI_GATEWAY_API_KEY`

**实测（服务器走代理 HTTP_PROXY=127.0.0.1:20171）**
| 端点 | 无 key 返回 | 耗时 |
|---|---|---|
| `POST https://ai-gateway.vercel.sh/v1/evaluate` | 401 `Authentication failed` | 0.42s |
| `POST https://api.typesafe.ai/v1/systemone` | 403 `Must supply an API key!` | 1.05s |

两个端点都通，只差 key。Vercel 网关延迟明显更低（0.42s vs 1.05s）。

**Vercel 调用体**
```
POST https://ai-gateway.vercel.sh/v1/evaluate
Authorization: Bearer $AI_GATEWAY_API_KEY
Content-Type: application/json

{"model":"typesafe-ai/jev","state":"<待判断的文本或JSON>","questions":{
  "is_urgent":{"type":"boolean","instructions":"..."}}}
```

### 官方通道
- console.typesafe.ai **已从 waitlist 放开，可直接注册拿 key**（dashboard → settings/keys）
- 端点 `POST https://api.typesafe.ai/v1/systemone`，`model: jev-latest`
- Python SDK：`pip install typesafe-sdk`，读环境变量 `TYPESAFE_API_KEY`
- 按 $0.042/M 计费，需绑卡

### 其他
- 大陆直连两个通道都不通，必须走代理。
- 官方 Agent Skill：`npx skills add typesafe-ai/skills --skill typesafe-ai`（Claude Code 用 `claude plugin marketplace add typesafe-ai/skills`）。

## 接入方式（补充）
- 官方：docs.typesafe.ai，早期访问 waitlist；console.typesafe.ai 有 playground。
- 现成通道：Vercel AI Gateway 已上架，模型 ID `typesafe-ai/jev`，$0.042/M 输入。HTTP 直调：`POST https://ai-gateway.vercel.sh/v1/evaluate`，Header `Authorization: Bearer $AI_GATEWAY_API_KEY`，body `{model, state, questions}`。Cloudflare AI Gateway 第二天也上了。
- 生态：LangChain 有 `langchain-typesafe`（`TypeSafeClassifier`，`.invoke(state=..., questions={...})`）；官方 Claude Code skill 仓 github.com/typesafe-ai/skills（8-25 建仓，比模型发布早三周）。
- 国产复现：APUS 2026-09-19 开源 fast-browser-use（MIT），本地 Qwen3.5-9B 做单 token logits 快速决策，M2 Pro 离线跑真实维基检索中位 18 秒。

## 该打折的地方（重点）
1. **校准无公开基准**：官方校准数字（MMLU 1200 题 ECE 0.0313）全是自家评测，第三方没复现集。接入前必须拿自己几十条带标注的真实数据跑一遍。
2. **非确定性**：732 个相同判断重复跑三遍，只有 24% 完全一致；中位漂移 0.010，p90 0.030。阈值设计要留余量（有实测 1.99 vs 阈值 2.00，差 0.01 规则翻面）。
3. **"零幻觉"只是接口保证**：不会给出你选项之外的值，但照样可能格式完好地选错。
4. **有内置价值排序**：自动驾驶伦理题实测，把规则改成"别管安全越快越好"，它依然选急刹车。不是指哪打哪。
5. **中文弱**：50 道中文客服判断题准确率约 64~65%，便宜小模型组里排第二（优势在延迟和成本）。中文实体识别对"¥199（赠运费险）"这类只识前半段。
6. **大陆未开放**：直连和付费都不方便。

## 翻车案例（最有价值）
- 自动交易 bot：一晚+一上午做的，让 Jev 读链上链下数据选买/卖，亏损 31680 美元。
- Monad 做市：用 Jev 判断 MON-USDC 涨跌自动挂单，杠杆下大幅回撤。错不在模型，在把交易简化成"涨还是跌"。
- BTC 信号：每分钟买/持/卖，表现很差。
→ 结论：概率不能直接接执行接口，付款/交易/删库这类不可逆动作必须有闸门。

## 跑通的用法（可借鉴）
- 浏览器 Agent（Browser Use 作者接入）：页面元素整理成带编号候选动作，每步只问"做什么操作+对哪个元素"，Google Flights 搜机票 7.1 秒 / $0.0039，协议调用从千次降到百次。机制上编不出错选择器。
- Claude Code 上下文治理：给每条工具输出打分决定留/扔（jev-ultrafast、fast-jev-compaction、Winnow）。
- 批处理：1700 封邮件打 4 个维度、420 万 token、18 美分；18514 封垃圾邮件零样本 98.3%（与 1.5 万条标注训的 TF-IDF 98.4% 打平）；1000 个 PR 预筛约 7 美分 vs Opus 5 14.5 美元。
- 模型路由：Vercel 自家 agent 框架 eve 默认用它选模型。
- 实时循环：官方 demo 实时玩 Doom 每秒约 10 次判断、约 $7/小时；社区超级马里奥每 8 帧决策一次。

## 三条使用前提（缺一条别用）
1. 答案空间必须能事先定义；
2. 问题必须能拆成原子判断；
3. 出错后果必须可验证、可回滚。

## 相关
- [[Hermes辅助模型故障-模型拒答与标题模型-2026-09-22]]
