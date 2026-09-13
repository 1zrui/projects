# Hermes 升级到 v0.21.1 记录（2026-09-11 22:55）

## 结果
- 云上从 **v0.20.5（2026.8.19，HEAD 8/26）** → **v0.21.1（2026.9.7）**，代码 HEAD `433d4068`（今天）
- 官方 `hermes update --check` 提示落后 96 个提交；更新后距 GitHub main 只差 1 个提交（cnb 镜像还没同步到）
- 更新方式：**QQ 里发 `/update`**（这条通道可用，会自动拉代码/装依赖/迁配置/重启网关），网关 22:57:54 重启，约 60 秒恢复
- `hermes doctor`：基本全绿，只剩 2 个 npm 漏洞（browser tools、web workspace）

## 96 个提交的内容分布
desktop 37 个、state/session 存储 29 个（state.db 损坏恢复、FTS 索引抢救、导出性能）、其余为 cli/web/tui/gateway/cron 小修。没有大新功能。

## ⚠️ 报错"更新失败"是虚惊（2026-09-11 23:00 复核）
更新末尾报：`⚠ Update incomplete — gateway auto-restart failed: cannot import name 'base_url_origin' from 'utils'`，并提示手动 `hermes gateway restart`。
复核结论：**实际没坏**。
- 报错根因：自动重启那一步，**旧网关进程内存里还挂着旧模块**（mixed sys.modules），去导入刚换的新代码时符号对不上 —— 瞬时状态，不是代码坏了
- 现在正在跑的网关 pid 861863 = **`@ 433d4068`**（`hermes update --plan` 报的），与磁盘代码同一 commit → 没有混版
- systemd 在 22:57:54 把新网关拉起来了，之后 `gateway.log` 零报错
- `hermes doctor`：版本文件一致 0.21.1、config v42 已最新、依赖齐、关键模块编译通过

排查套路：
```bash
hermes update --plan          # 看"运行中的网关到底在跑哪个 commit"（@ 后面那段）
systemctl --user is-active hermes-gateway
grep -iE "error|traceback" ~/.hermes/logs/gateway.log | tail
```

## ⚠️ 踩坑：升级会 stash 本地补丁，而且可能重放不了
- 更新后生成了 `git stash stash@{0}: hermes-update-autostash-20260911-145504`
- 里面是**我们的 NapCat/QQ 本地补丁**，7 个文件：`gateway/authz_mixin.py`、`gateway/config.py`、`gateway/platforms/qqbot/adapter.py`、`gateway/run.py`、`hermes_cli/platforms.py`、`tools/url_safety.py`、`toolsets.py`
- 未跟踪文件（`gateway/platforms/napcat.py`、`napcat_api.py`、`tools/qq_tool.py`、`skills/qq/`）**没被动**，还在
- **`git stash apply --check` 报 6 个文件冲突** → 不能干净重放，得对着新代码重新打
- 影响：**实测不需要了** —— 2026-09-11 23:02 大哥从 QQ 发图，媒体下载正常（`qqbot/adapter.py` 那段绕过代理的补丁在 v0.21.1 已无必要，上游自己修好了）
  - napcat 侧：`config.yaml` 里 `napcat.enabled: false`，暂时无影响
- 补丁已导出存档：`~/workspace/patches/hermes-napcat-qq-patch-20260911.patch`（7 个文件，8.6KB），哪天要启用 napcat 再照着改
- 检查口令：`git stash list` / `git status --porcelain`（`*.napcat.bak` 是补丁前的备份）

## 命令备忘
```bash
hermes --version                      # 看版本
hermes update --check                 # 只预览有没有更新
hermes update --plan                  # 看会重启哪些服务
hermes update                         # 更新（终端跑）
/update                               # QQ/Telegram 等平台内更新
git stash list                        # 升级后检查补丁有没有被 park
```
