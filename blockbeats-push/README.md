# 律动 (BlockBeats) 快讯实时推送

把 BlockBeats（律动）的快讯**准实时**推到指定 QQ 群：每 20 秒抓一次快讯列表页，有新快讯就渲染成
报刊风卡片图发群（发图失败自动降级发全文文字）。

```
BlockBeats 快讯页(SSR HTML)
   │  每 POLL 秒拉一次（直连优先 → 失败走代理兜底）
   ▼
解析：/flash/{id} + 标题 + HH:MM + 正文
   │  去重：只处理 id > last_max_id（state 持久化，重启不重发）
   ▼
过滤：默认全发，仅黑名单拦明显非币圈的（世界杯/演唱会/股票/A股…）
   ▼
渲染：Pillow 直画 640px 报刊风卡片（时间+标题+红条+全文正文+链接+署名）
   ▼
发送：qqbot 官方 REST → 上传媒体拿 file_info → 发 msg_type=7 媒体消息
        （任一步失败 → 降级发 msg_type=0 纯文字，依旧全文不截断）
```

---

## 1. 目录结构

```
blockbeats-push/
├── blockbeats_listener.py     # 主程序（常驻进程，自带 5 秒自愈重启）
├── config.example.env         # 配置模板 → 复制成 .env 填值
├── requirements.txt           # 依赖：只有 Pillow
├── README.md                  # 本文档
├── deploy/
│   ├── blockbeats-push.service  # systemd 单元（Linux 云服务器用）
│   └── install.sh               # Linux 一键部署脚本
├── state/last_id.json         # 运行期生成：已推送到的最大 id（去重进度）
├── logs/listener.log          # 运行期生成：日志
└── cache/flash_<id>.png       # 运行期生成：卡片图缓存
```

**零密钥入库**：`QQ_CLIENT_SECRET` 只写在 `.env`（已在 `.gitignore` 里），代码/仓库里没有任何密钥。

---

## 2. 云服务器部署（Ubuntu / Debian · systemd）

### 方式 A：一键脚本（推荐）

```bash
# 1) 把整个 blockbeats-push 目录传到服务器（scp / git clone 都行）
scp -r blockbeats-push root@<服务器IP>:/root/

# 2) 进目录执行安装（默认装到 /opt/blockbeats-push）
ssh root@<服务器IP>
cd /root/blockbeats-push
sudo bash deploy/install.sh            # 或 sudo bash deploy/install.sh /opt/blockbeats-push

# 3) 填密钥
vi /opt/blockbeats-push/.env           # 填 QQ_APP_ID / QQ_CLIENT_SECRET

# 4) 启动 + 看日志
systemctl start blockbeats-push
journalctl -u blockbeats-push -f
```

`install.sh` 会：装 `python3-venv` + `fonts-noto-cjk`（**中文卡片必需**）→ 建 venv 装 Pillow →
生成 `.env`（chmod 600）→ 注册 `blockbeats-push.service` 并设为开机自启 → 跑一次 `--check` 自检。

### 方式 B：手动部署

```bash
apt-get update && apt-get install -y python3-venv python3-pip fonts-noto-cjk
mkdir -p /opt/blockbeats-push && cd /opt/blockbeats-push
# 放入 blockbeats_listener.py / requirements.txt / config.example.env
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp config.example.env .env && chmod 600 .env && vi .env
mkdir -p state logs cache
# systemd
cp deploy/blockbeats-push.service /etc/systemd/system/
sed -i 's#/opt/blockbeats-push#/opt/blockbeats-push#g' /etc/systemd/system/blockbeats-push.service
systemctl daemon-reload && systemctl enable --now blockbeats-push
```

---

## 3. 配置项（`.env`）

| 变量 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `QQ_APP_ID` | ✅ | — | QQ 开放平台机器人 AppID |
| `QQ_CLIENT_SECRET` | ✅ | — | 机器人 AppSecret（**密钥，勿入库**） |
| `BB_GROUP_OPENID` | | `8DDF1613...D9201` | 目标群 openid（**不是群号**）。换群 = 先让机器人在该群被 @ 一次，再从网关日志 `group_openid=` 拿 |
| `BB_POLL` | | `20` | 拉取间隔（秒），最小 5 |
| `BB_SOURCE_URL` | | 官网快讯页 | 数据源变了改这里 |
| `BB_PROXY` | | 空 | 代理兜底，例：云服务器 v2rayA `http://127.0.0.1:20171` |
| `BB_STATE_FILE` / `BB_LOG_FILE` / `BB_CACHE_DIR` | | 项目内 | 运行期文件路径 |
| `BB_FONT_REGULAR` / `BB_FONT_BOLD` | | 自动探测 | 中文字体路径（Linux 装了 `fonts-noto-cjk` 会自动找到） |

---

## 4. 部署验收（三步，务必都过）

```bash
cd /opt/blockbeats-push

# ① 抓取解析自检（不发群）：应打印解析到的条数 + 最新 id + 字体探测结果
.venv/bin/python blockbeats_listener.py --check

# ② 卡片渲染自检（不发群）：生成 cache/preview.png，下载看一眼排版
.venv/bin/python blockbeats_listener.py --preview "测试标题在这" "这是正文，用来检查换行和排版是否正常。" --time 12:34

# ③ 通道实测（会往群里发一张测试卡）：群里收到 = 整条链路通
.venv/bin/python blockbeats_listener.py --test-send

# 然后启动常驻
systemctl start blockbeats-push && systemctl status blockbeats-push
```

日志里正常长这样：
```
[2026-09-12 17:40:03] 启动监听 | 源=... | 目标群openid=8DDF16... | 间隔=20s | last_max_id=364511 | 代理=无
[2026-09-12 17:40:03] qqbot token 获取成功，通道就绪
[2026-09-12 17:41:07] 推送图片 id=364512 发送=OK | 某交易所获准...
```

---

## 5. 运维

> ⚠️ **同一个群只能跑一个实例**：本机（Windows）与云服务器同时跑 = 每条快讯推两遍。
> 从本机迁到云上时，先在云上验收通过，再 `taskkill` 掉本机那个监听器（查：
> `wmic process where "name='python.exe'" get ProcessId,CommandLine | findstr blockbeats_listener`）。

| 操作 | 命令 |
|---|---|
| 启停/重启 | `systemctl start\|stop\|restart blockbeats-push` |
| 状态 | `systemctl status blockbeats-push` |
| 实时日志 | `journalctl -u blockbeats-push -f`（或 `tail -f logs/listener.log`） |
| 改配置 | 改 `.env` → `systemctl restart blockbeats-push` |
| 改代码 | 覆盖 `blockbeats_listener.py` → `systemctl restart blockbeats-push` |
| 开机自启 | 安装时已 `enable`；`systemctl is-enabled blockbeats-push` 可查 |

**重启不重发**：进度在 `state/last_id.json`（只存一个整数）。想补发历史：把该数字改小
（如 `{"last_max_id": 364500}`）再重启，会把 364501 之后的都推一遍；**注意别改得比快讯源的历史更早**，
否则会补几十条。

---

## 6. 排障

| 症状 | 排查 |
|---|---|
| 日志 `[err] 直连拉取失败/代理也失败` | 服务器出网问题。先 `curl -I https://www.theblockbeats.info/newsflash/rss`；不通就配 `BB_PROXY`（本机 v2rayA 是 `http://127.0.0.1:20171`） |
| 日志 `[fatal] qqbot token 获取失败` | `.env` 里 `QQ_APP_ID` / `QQ_CLIENT_SECRET` 错或过期；也可能是服务器出网到 `bots.qq.com` 不通。脚本会 5 秒自重启重试，systemd 也会兜底 |
| 卡片中文变方块 □ | 服务器没中文字体：`apt-get install -y fonts-noto-cjk`，或 `BB_FONT_REGULAR` 指到具体 `.ttc/.otf`。`--check` 会直接打印字体探测结果 |
| 群里收不到，但日志说 `发送=OK` | ① openid 对不对（换群必须重拿）② 机器人还在群里吗（被移出会报"群已注销"）③ 看是否降级发文字了 |
| `qqbot API ... HTTP 400` | 常见是 `file_info` 上传失败或文本超 4000 字（脚本已截断）。看日志里上一条 `[warn] qqbot 图片链路失败` 的原文 |
| 快讯源变成空/报错 | BlockBeats 又改版了（历史上 REST API 404 废弃过一次）。`--check` 会打印解析条数；条数为 0 就看 `_parse_page()` 里的正则是否要跟着页面结构改 |
| 同一快讯反复推 | `state/last_id.json` 被清空/回滚了。恢复正常后它只增不减 |
| 进程活着但不推 | 看 `logs/listener.log` 最新时间戳；卡住不动 = 拉取环节在超时（`BB_POLL` 秒后自动重试，不会退出） |

---

## 7. 设计说明（改代码前先读）

- **去重语义**：`last_max_id` 是单调递增的进度指针。**每条真正发送成功后才推进**；
  被黑名单过滤的条目也推进（否则会被反复重拉），但会打 `跳过(不相关)` 日志留痕。
  历史教训：早期版本把 `save_state` 写在循环外，导致"整批被过滤 = 进度照推 = 静默丢快讯"。
- **过滤策略**：BlockBeats 本身就是加密快讯源 → **默认全发**，只用 `BLACKLIST` 拦明显非币圈
  （世界杯/演唱会/股票/A股…）。历史教训：早先用关键词白名单，误杀率 90%+（把"特朗普石油储备"
  这类重磅也丢了）。
- **渲染**：Pillow 直画（A 模式），不依赖浏览器/截图。`wrap()` 按当前字体实测宽度逐字符换行，
  标题 28 号加粗、正文 16 号、链接 12 号蓝、底部署名。
- **emoji 坑**：微软雅黑/Noto Sans CJK 不含彩色 emoji 字形，卡片里放 ⏰/⚡ 会变豆腐块 →
  卡片时间只放 `HH:MM` 数字，品牌位用红色方块 + 白字 `F`。
- **自愈**：外层 `while True: try main() except → 5 秒后重启`，配合 systemd `Restart=always` 双保险；
  致命错误（token 拿不到）也不裸退。
- **依赖极简**：只有 Pillow（画图）。拉取/发群/JSON 全是标准库 → 云服务器上装依赖几乎不会翻车。

---

## 8. 变更记录

- **2026-09-12** 整理成可部署项目：跨平台字体自动探测、配置全部环境变量化、`BLOCKBEATS_API_KEY`
  不再是硬性要求（REST API 早已废弃）、新增 `--check/--preview/--once/--test-send` 四个运维模式、
  补齐 systemd 单元与一键安装脚本、README。
- **2026-09-11** 通道改 qqbot 官方 REST（弃 NapCat）；目标群 631502972。
- **2026-08-31** 与 Hermes 网关彻底解耦（独立进程 + 自愈壳）；卡片改报刊风；轮询 30s→20s。
- **2026-08-30** 数据源从废弃的 REST API 换成官网 SSR 页解析；过滤改"默认全发 + 黑名单"。
