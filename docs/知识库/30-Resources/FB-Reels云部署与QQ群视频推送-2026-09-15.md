# FB Reels 云部署 + QQ 群视频推送（2026-09-15）

## 部署位置
- `/opt/fb-reels/`（scripts + data + .env，venv 在 `.venv`）
- 凭证：`.env`（600）用**云上自己的 qqbot**（appid `1905595541`），不是包里默认那套
- 目标群：**消息推送**（数字群号 624127517），group_openid = `7861772C9D3065DF0986CAE70EF94435`
  - 群 openid **随 appid 变**！包里内置的 `1EBBE3BD…` 是本机 appid 的，云上用会失败
  - 查法（实测可用）：`GET /v2/groups/{group_openid}/info` → 回群名/人数，可反向验证 openid 对不对

## 与原始包的四处必要改动（踩出来的）
| 改哪 | 原样 | 改成 | 为什么 |
|---|---|---|---|
| 群 openid | 包里内置（本机 appid 的） | 云端 appid 下实测值 `7861772C…` | openid 跟 appid 绑定，换了 appid 全失效 |
| 转码 | libx264 **baseline** CRF23 | **libx265** + **码率对齐原片** | FB 原片是 **AV1**（抖音不认）；baseline 重压把 54MB 吹成 148MB（2.7 倍） |
| CPU 限制 | 无 | **`-x265-params pools=2`** | x265 **无视 taskset** 自己抢满 4 核 → 打满 CPU → 触发 new-api 的 CPU>90% 熔断 → 模型调用 503 |
| part_finish | 失败即抛错 | **失败重试 6 次** | 40093001「分片转存 BDH 通道异常」是**瞬时错误**，实测同一片连续失败 3~5 次后自动通过 |

## QQ 官方机器人 API 关键坑（都在官方文档里，实测踩过）
1. **视频软限制 30MB / 硬限制 200MB**；超软限会"降级为文件类型"上传
2. **40093001 = 分片转存 BDH 通道异常，官方原话"请重试"** → 必须重试，否则整条片子白传（这是"视频传不上去"的真凶）
3. 上传方式只有两种：**分片上传**（推荐）和 **URL 直传**（给 URL 让平台自己下载）。没有"直接 POST 一个本地文件"的接口
4. 消息类型：`msg_type=7` + `media.file_info` 才是富媒体；`file_info` 必须先上传换取
5. 主动消息频控：群 20/qpm、每群每天 1000 条（不是传说中的每月 4 条）
6. 上传慢不是脚本问题：本机上行只有 **2.6Mbps**（腾讯云套餐上限），10MB 分片约 32 秒

## 实测数据（同一条 72 秒原片）
| 方案 | 编码 | 码率 | 体积 | 上传 | SSIM | CPU 峰值 |
|---|---|---|---|---|---|---|
| 原片 | AV1 | 6.16M | 54MB | — | 1.0000 | — |
| 原脚本 | H.264 baseline | 17M | 148MB | 9.5分 | 0.9785 | 100% ❌ |
| 新方案 | **H.265** | 5.87M | **52MB** | **3.5分** | **0.9619** | **62%** ✅ |

- SSIM 0.96 已在"肉眼难辨"区间；抖音收到后还会二次压缩，这点差距基本被抹平
- AV1 → H.265 属重压，**"SSIM=1.0（完全无损）"物理上做不到**，只能靠加码率逼近

## 验收结果（2026-09-15 23:13 真实管线）
抓取 ✅ → 下载原片 ✅ → H.265 转码（52MB）✅ → 上传（1 片重试后通过）✅ → 发群 ✅ → 回执 ✅，退出码 0

## 可靠性优化（2026-09-15 晚，目标"到点必须能收到视频"）
| 改哪 | 原样 | 改成 | 为什么 |
|---|---|---|---|
| fb1 超时跳过记账 | 正则 `> \d+s` | `> [\d.]+s` | download 打印的是 `> 40.0s`（浮点），原正则永远匹配不上 → 同一条超时片每轮被重报、skipped 名单永远为空 |
| fb1 转码超时 | 600s（默认） | **1800s**（下载 600→900s） | 转码是一次调用转整个目录（最多 5 条），x265 每条约 5 分钟 → 2 条以上就被掐断 → `run` 返回 None → 整条管线 exit 3 |
| Chrome profile | 共用默认 profile | 每端口独立 `--user-data-dir=work/chrome-profile-<port>` | 桌面 Chrome（CDP 9222）或另一个池在跑时，新进程会转交给已有实例并退出，`--remote-debugging-port` 失效 → 抓取必挂 |
| 归档保留 | 7 天 | **3 天** | 40 秒片每条约 55MB（raw+dy），7 天可能吃掉几 GB；磁盘只有 40G |

## 时长城门：上限 40s + 下限 8s（2026-09-16，大哥看到 fb2 发了条 5s 的）

**问题**：fb2 推了一条 5 秒的视频（挂不上完整剧情）。查 catalog 发现：**按播放量排序选片时，短片子因播放量高反而排前面** →
```
catalog 分布：<8s = 200 条 ｜ 8-40s = 667 条 ｜ >40s = 743 条
被选中的那两条正是 5.233s(25万播放) 和 5.056s(31万播放)
```

**修法**（两条管线选片逻辑不同，得分别改）：

| 池 | 原逻辑 | 加下限 |
|---|---|---|
| **fb1** | `download_reels.py <state> <dir> 5 40`（第4参=上限） | 新增第5参 `min_duration_s`，缺省读 `FB_MIN_DURATION`=8；`< 下限` 打印 `[skip] <rid>: 5s < 8s` |
| **fb2** | 自己按 catalog / `probe()` 过滤 `dur > CAP` | 新增 `FLOOR = FB_FB2_FLOOR`（缺省 8），两处都改成 `dur > CAP or dur < FLOOR` |

**关键坑**：fb1 的 cron 靠正则从 download 输出捞跳过的 rid 写进 `state.skipped_reel_ids`，否则**同一条短/长视频每轮都被当"新视频"重复报**。加下限后正则必须同时吃两种写法：
```python
re.findall(r"\[skip\] (\d{10,}): .+ (?:> [\d.]+s|< [\d.]+s)", dl_out)
```
（已实测三种输出格式都能匹配 ✓）

**环境变量**：`FB_MIN_DURATION`（fb1）/ `FB_FB2_FLOOR`（fb2），不改 `.env` 就是默认 8s；上限仍由 `FB_FB2_CAP`=40s 控制。

## 待办
- [x] **定时已接入**（2026-09-15 23:30）——`crontab` 装入 `deploy/fb-reels.cron` 共 10 行；cron 服务 active+enabled；`CRON_TZ=Asia/Shanghai`；干净环境（`env -i` 模拟 cron）两池自检全过
  - fb1：工作日 11:50 / 17:20 / 21:00 / 00:20；周末每 3 小时（整点）
  - fb2：工作日 11:30 / 17:00 / 20:30 / 00:00；周末每 3 小时（:30）
  - 日志：`/opt/fb-reels/logs/fb1.log`、`fb2.log`；脚本自带 ±3min 时间门兜底
  - ⚠️ cron 环境**没有** HTTP_PROXY → QQ API 走直连（比我手动跑更快）
- [x] 本机 Windows 的 fb1/fb2 已由大哥停掉（2026-09-15 晚确认），不会双推
- [x] 时长上限：**已定 40 秒**（2026-09-15 大哥令）——fb1 硬编码 `"40"`，fb2 默认 `FB_FB2_CAP=40`（.env 可覆盖）；实测 72 秒那条被 `[skip] … 1:12 > 40.0s` 正确跳过
- [ ] 无下限过滤，catalog 里有 3~5 秒的短货（大哥暂未要求处理）
- [ ] 转码偏慢（40 秒片约 5 分钟）：x265 比 x264 慢约 2 倍，这是换画质的代价；要提速可调 `-preset faster` 或 `pools=3`（未做）
- [ ] frps（双机隧道）处于 disabled 状态，大哥说本机不用管，暂不启用

---

## 2026-10-22 更新：新增 fb3 池 + catalog 排序修复 + 图片发送踩坑

### fb3 三号池（泰国吃播 kinkubky）
- 主页：`https://www.facebook.com/kinkubky?sk=reels_tab`（分享链接 `share/18hur8otcg` 重定向后可得主页名；数字 ID `100063617095771` 从页面 `fb://profile/` 字段拿）
- 脚本：`scripts/cron_fb_reels_pool3.py`（**复制自 pool2 改造**，不是手写）
- 配置在 `fb_common.py` 加了 `FB3_STATE/WORK/CATALOG`；`selfcheck` 也要支持 `pool=="3"`
- state：`data/state_100063617095771.json`；catalog：`data/fb3_reels_catalog.csv`（**空，catalog 不会自动追加，需手动维护** → 目前 fb3 无顶替素材）
- CDP 端口：**9335**（fb1=9333 / fb2=9334 / fb3=9335 互不冲突，各端口独立 Chrome profile）
- 推群：同 624127517（GROUP_OPENID `7861772C9D3065DF0986CAE70EF94435`）

### 三池时间排程（互不重合）
| 池 | 工作日 | 周末 |
|---|---|---|
| fb1 | 11:50 / 17:20 / 21:00 / 00:20 | 每 3h 整点 |
| fb2 | 11:30 / 17:00 / 20:30 / 00:00 | 每 3h :30 |
| **fb3** | **11:10 / 16:40 / 20:10 / 23:40** | **每 3h :45** |

- 时间门在脚本内 `_TIME_GATE_WHITELIST` + `_WEEKEND_SLOT_MIN` + `_is_catalog_slot`（对应顶替窗口）
- crontab：`deploy` 或 crontab -e，日志 `logs/fb3.log`（需先 `touch`，cron 重定向不会建文件）

### catalog 顶替排序修复（fb1/fb2 都改）
- **问题**：顶替按播放量取前 12 条，top12 全是 2024-2025 老片 → FB 老片源片只有 360p/540p → 被 720p 画质闸全挡 → 一条都发不出（2026-10-22 fb2 实测）
- **修法**：`candidates.sort(key=lambda x: x[3], reverse=True)` 按**日期新→旧**优先排序，候选放宽到 `picks = candidates[:20]`，元组加 date 字段
- 已发池排除逻辑不变（`fbX_sent_pool.txt`）

### 图片发送踩坑（QQBot API）
- **`file_type`：1=图片 2=视频 3=语音 4=文件**。发图传 3 会报 `40093008 音频转换失败`
- 完整流程：`upload_prepare(file_type=1)` → 分片 PUT → `part_finish` → `files` 合并拿 `file_info` → 发消息 `msg_type=7` + `media.file_info`
- URL 直传（`files` 带 `url`）会报 `40093007 富媒体文件下载失败`（平台从 fbcdn 拉不动），本地下载再分片上传才稳
- 头像抓取：打开主页取 `meta[property="og:image"]`（720x720 高清版），curl 带 UA 下载

### 手动验证管线注意
- 手动跑要 `FB_FORCE_RUN=1` 绕时间门
- **timeout 要给足**（5 分钟会掐断 30s 片转码 → `_record` 记账没执行 → 视频已推但 state 没记 → 会重复推）。验证用后台跑 + `notify`，或 timeout ≥ 900s
- 若视频推了但 `last_sent_reel_ids` 空：手动补 state + `fb3_sent_pool.txt`，防重复推
- check_reels 基线是 `last_sent_reel_ids`（已发），不是 last_seen；已发池非空后其余候选都算"新"

### 标题抓取 + 泰文翻译中文（2026-10-22，fb1/fb2/fb3 三池统一）
- **抓标题**：yt-dlp `--skip-download --print "%(title)s"`（走 PROXY），一小时前实测 FB title 格式
  `"14M views · 266K reactions | <描述> | <博主名>"` → split("|") 去掉头尾保留描述主体，截 200 字符
- **翻译**：公共函数 `translate_title` 在 `fb_common.py`；`fetch_reel_title` 也在 fb_common（三池共用，改一处）
- **发群带标题**：`send_group_video(fp, title)` 的 content 用中文标题，空标题回落"FB N号池视频"
- `_fetch_and_send` 返回值从 2 元组改 3 元组 `(ok, reason, title)`，**两个调用点都要改成 `_ok, _why, _title =`**

### ⚠️ QQ 富媒体标题不显示的坑（2026-10-22 踩实）
- **`msg_type=7`（视频/图片富媒体）的 `content` 字段在 QQ 群聊里根本不渲染成文字**——只是内部备注
- 视频消息 content 塞标题 = 白传，群里看不到
- **必须单独发一条 `msg_type=0` 文本消息**把标题发出去，再发视频
- `send_group_video` 新版：有 title 时先发 `📝 {title}` 文本（msg_type=0），再传视频；`_qqbot_api` 的文本发送**不检查返回值也无妨**（手动验证可发通，QQ API 返回消息 id 即成功）
- 验证：手动重发归档里的 `dy.mp4` 文件 + 标题，即"📝 中文标题 + 视频"连发

### 翻译渠道踩坑（重要！）
- ❌ **Google 免费接口**（`translate.googleapis.com/translate_a/single?client=gtx`）能用但**短时间多调就 429 限流**，几分钟内连续几次就废 → 不适合生产管线
- ❌ **deepseek-v4-flash / glm-5.2 是思考型模型**，直接 chat/completions 会**吐空 content**（记忆里的坑在这也踩了）
- ✅ 用**本地 new-api**（`http://127.0.0.1:3000/v1`）模型 **`agnes-3.0-flash`**（普通对话模型），质量好、无外部依赖、不限流
- key 获取：优先环境变量 `FB_NEWAPI_KEY`，否则从 `~/.hermes/config.yaml` 正则提取（`api_key:\s*(sk-[\w]+)`），**不依赖 yaml 库**（fb-reels venv 没装 PyYAML）
