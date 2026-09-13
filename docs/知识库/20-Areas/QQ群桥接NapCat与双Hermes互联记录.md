# QQ 群桥接(NapCat)与双 Hermes 互联记录

> 日期：2026-08-16
> 状态：✅ NapCat 群桥接打通,双 Hermes 可通过 QQ 群自由交流
> 摘要：QQ 官方机器人群聊受限(沙箱无群配置)→ 改用 NapCat(OneBot 11)方案,云上 Hermes 接入第二个 QQ 号,在群里互 @ 实现双机交流。

## 一、背景与方案选型

### 需求
本地 Hermes(Windows)与云上 Hermes(Ubuntu)实现自由交流。

### 方案对比
| 方案 | 结论 |
|---|---|
| QQ 官方机器人群聊 | ❌ 沙箱模式无群聊配置(开放平台新机器人不开放群功能) |
| webhook 双向 | 部分可行:本地→云已通(8644),云→本地需 frp 或轮询 |
| **NapCat 群桥接** | ✅ **最终方案**:两台 Hermes 都接同一个 QQ 群,互 @ 即交流 |

### 关键认知
- 云上 Hermes v0.20.1 官方**不含** napcat 适配器(v0.18.0 有,后续版本移除)
- 社区方案:`shubyi/hermes-napcat`(PyPI 包,自动修补 Hermes + 安装 NapCat)
- 本地 Hermes(v0.18.0)的 napcat.py 正是这个包装的,不是官方自带

## 二、安装步骤(完整可复现)

### 1. 安装 hermes-napcat 包
```bash
export PIP_PROXY=http://127.0.0.1:20171 PIP_HTTPS_PROXY=http://127.0.0.1:20171
/home/ubuntu/.hermes/hermes-agent/venv/bin/python -m pip install hermes-napcat -i https://pypi.org/simple/
```

### 2. 修补 Hermes(注入适配器)
```bash
/home/ubuntu/.hermes/hermes-agent/venv/bin/hermes-napcat install
# 补丁内容:gateway/platforms/napcat.py + napcat_api.py + tools/qq_tool.py + config.py 注册 + toolsets + skill
```

### 3. 安装 NapCat 本体(坑最多的一步)
安装脚本从 GitHub 下载 NapCat.Shell.zip + 腾讯 CDN 下载 LinuxQQ,直连全慢/断。

**手动下载(走代理)放好再跑脚本:**
```bash
# NapCat.Shell.zip(29M)
curl -sL -m 300 --proxy http://127.0.0.1:20171 -o NapCat.Shell.zip \
  "https://github.com/NapNeko/NapCatQQ/releases/latest/download/NapCat.Shell.zip"
# QQ.deb(64M,腾讯 CDN 直连卡 67%,必须代理)
curl -sL -m 300 --proxy http://127.0.0.1:20171 -o QQ.deb \
  "https://qqdl.gtimg.cn/qqfile/QQNT/9.9.32/beta/727ce4e5/linuxqq_3.2.30-50828_amd64.deb"
# 跑安装脚本(检测到两个文件已存在会跳过下载)
bash /tmp/napcat_install.sh --docker n --cli y
# 安装位置:/home/ubuntu/Napcat
```

### 4. 配置 NapCat OneBot 反向 WS(连 Hermes 18800)
```bash
python3 << 'EOF'
import json, sys
sys.path.insert(0, '/home/ubuntu/.hermes/hermes-agent/venv/lib/python3.11/site-packages')
from hermes_napcat.napcat import build_napcat_config
cfg = build_napcat_config(ws_port=18800, http_port=18801, access_token="")
cfg_dir = '/home/ubuntu/Napcat/opt/QQ/resources/app/app_launcher/napcat/config'
import os; os.makedirs(cfg_dir, exist_ok=True)
open(os.path.join(cfg_dir, 'onebot11.json'), 'w').write(json.dumps(cfg, indent=2))
EOF
```

### 5. 配置 Hermes napcat 平台
```bash
hermes config set platforms.napcat.enabled true
hermes config set platforms.napcat.extra.http_api http://127.0.0.1:18801
hermes config set platforms.napcat.extra.self_id 2242413547
hermes config set platforms.napcat.extra.ws_port 18800
hermes config set platforms.napcat.extra.dm_policy open
hermes config set platforms.napcat.extra.group_policy open
```

### 6. 启动 NapCat + 扫码
```bash
# 必须 DISPLAY=:1(VNC 显示器),否则窗口在 xvfb 里看不到
export DISPLAY=:1
/home/ubuntu/Napcat/opt/QQ/qq --no-sandbox -q 2242413547
# 扫码方式:Chrome 打开 http://127.0.0.1:6099/webui?token=<webui token>
# webui token 在 /home/ubuntu/Napcat/opt/QQ/resources/app/app_launcher/napcat/config/webui.json
```

### 7. 重启网关(手动,会话内会被拦)
```bash
env -u _HERMES_GATEWAY hermes gateway restart
```

## 三、最终架构

```
本地 Hermes (Windows, NapCat)
    ↕ QQ 群 1064105365 互 @
云 Hermes (Ubuntu, NapCat + 机器人号 2242413547)
```

- 群共享会话(group_sessions_per_user: false 默认)
- 群聊需 @ 机器人触发
- 私聊直接发

## 四、关键坑位

1. **xvfb vs VNC 显示器**:`xvfb-run` 启动窗口在虚拟屏,用户看不到。必须 `DISPLAY=:1`(VNC)启动,窗口才在桌面
2. **腾讯 CDN 下载 LinuxQQ**:直连卡 67%,必须走代理(127.0.0.1:20171)
3. **NapCat.Shell.zip 被脚本 clean 删除**:重跑脚本前确认文件还在,不在就重新下载
4. **安装脚本要求 NapCat 目录不存在**:手动解压过的要移走
5. **网关重启**:装完 napcat 平台必须重启网关才加载(会话内被拦,用 `env -u _HERMES_GATEWAY hermes gateway restart`)
6. **WebUI 登录**:6099 端口 + token,浏览器打开选"扫码登录",手机 QQ 扫码
7. **封号风险**:NapCat 是逆向协议,QQ 号有被风控风险

## 五、当前状态
- 云 Hermes 机器人号:2242413547
- 群:1064105365(已通)
- NapCat WebUI:6099(token 在 webui.json)
- 本地群白名单:445141066 / 631502972 / 955470254

## 六、GitHub 桥接(替代 NapCat 的最终方案)

### 背景
NapCat 已停用(封号风险 + 官方协议更稳)。改用 GitHub Issue 通道实现双 Hermes 主从协作。

### 架构
```
你 → 本地 Hermes(主,无公网)
     │ 发任务 Issue(出站✅)
     ▼
GitHub 1zrui/hermes-bridge(私有仓库)
     │ webhook → 云上 8644 ✅
     ▼
云上 Hermes(从,带 terminal/file/web 执行) → 评论回复(1次)
     ▼
本地 Hermes 轮询评论(出站✅)
```

### 配置步骤(已验证)
1. **GITHUB_TOKEN**(fine-grained):Issues Read/Write + 只授权 hermes-bridge 仓库。本地云上共用同一个。失效特征:API 返回 Bad credentials
2. **创建 webhook 订阅**(云上):
```bash
hermes webhook subscribe github-bridge \
  --events "issues,issue_comment" \
  --prompt "【任务派发】...执行后用 curl 调 GitHub API 评论回复(汤圆: 开头)" \
  --deliver qqbot --deliver-chat-id 51D786D4C3D4B91C69D99CB83887F3E3
```
3. **GitHub 仓库配 webhook**(API):`http://119.29.238.30:8644/webhooks/github-bridge` + HMAC secret(注意:每次重建订阅 secret 会变,要同步更新仓库 webhook)
4. **挂过滤脚本**(关键防循环):`~/.hermes/scripts/github_bridge_filter.py`
   - 判断逻辑:评论以"汤圆:"开头 → 云上自己的回复 → 拦截;新任务 Issue(opened)→ 放行;delivery 去重
   - ⚠️ 必须从 payload 判断事件类型,不能依赖 WEBHOOK_EVENT 环境变量(平台不传!)
5. **toolsets 配置**:订阅 JSON 里加 `"toolsets": ["terminal","file","web","search"]`(让云上 agent 能干活)

### 关键坑位(重复评论问题)
- **现象**:一个任务被评论 3 次
- **根因**:云上评论 → 触发 issue_comment webhook → 新 agent 又评论 → 循环
- **修复**:过滤脚本拦截"汤圆:"前缀评论 + delivery 去重
- **v1/v2 失败教训**:
  - v1 按 sender 账号判断(1zrui)→ 误杀本地(共用账号)
  - v2 依赖 WEBHOOK_EVENT 环境变量 → 平台不传,判断失效
  - **v3 正解**:从 payload 判断(comment.body 前缀 + action 字段)

## 七、辅助模型 503 修复(代理冲突)

### 现象
辅助模型(title/vision 等)报 503,但中转站直调正常

### 根因
给网关加 HTTPS_PROXY(为 Gemini TTS)→ **代理拦截了 localhost 中转站请求** → 503

### 修复
systemd drop-in 加 NO_PROXY:
```
~/.config/systemd/user/hermes-gateway.service.d/proxy.conf:
Environment="NO_PROXY=127.0.0.1,localhost,::1"
```
.env 同步 NO_PROXY。重启网关生效。

### 教训
给网关配代理时,必须同时配 NO_PROXY(本地服务绕过),否则本地中转站/localhost 服务全被代理搞挂。
