# Hermes `/restart` 执行逻辑 & Windows 上"只杀不拉"的原因（2026-09-12）

大哥本地 Hermes（Windows）发 `/restart` 只把网关杀掉，没有拉起来。代码级排查结论：

## /restart 的三步
1. 写标记：`.restart_notify.json`（记请求者，重启后回来通知）、`.restart_last_processed.json`（防平台重投递导致重启循环）
2. 判定"我有没有托管者"（`gateway/restart.py::is_gateway_supervisor_process()`），**只看 4 个标记**：
   `INVOCATION_ID`(systemd) / `HERMES_S6_SUPERVISED_CHILD` / `XPC_SERVICE_NAME`(launchd) / `HERMES_GATEWAY_EXTERNAL_SUPERVISOR`
3. 分两条路：
   - **有托管者** `via_service=True` → drain 完 `exit 75` → systemd（`RestartForceExitStatus=75`）重拉
   - **没有** `detached=True` → 起一个隐藏 watcher（`python -c <watcher> <旧pid> <延时> hermes gateway restart`，CREATE_NO_WINDOW + 尝试 BREAKAWAY_FROM_JOB），等旧进程退出后自己跑 `hermes gateway restart`；**旧进程以 exit 0 退出**

## 为什么 Windows 上会"只杀不拉"
1. Windows 计划任务给网关设的是 `HERMES_SUPERVISED_CHILD=1` + `HERMES_GATEWAY_DETACHED=1`，**这两个偏偏不在第 2 步那张名单里** → 永远判成"没有托管者" → 永远走 watcher 路。
   （注：`hermes_cli/main.py` 的 supervised 判定**认** `HERMES_SUPERVISED_CHILD`，两处判定不一致，是真正的坑）
2. watcher 若起不来/被带走：由于父进程在 Job Object 且不允许 breakaway（桌面端托管/某些终端）→ `Popen` OSError → 日志只有一条 WARNING `Detached restart watcher was not started after the no-breakaway retry`；watcher 自己的 stdout/stderr 全进 DEVNULL，**它启动后失败则完全无日志**
3. 退出码是 **0** → 计划任务的 `RestartOnFailure`（PT1M / 999 次）只对失败退出生效，exit 0 被当正常完成 → 也不补拉

两条一起失效 = 网关死透，只能手动起。云上没这问题：systemd 会设 INVOCATION_ID → 走 exit 75 → 被 systemd 拉回。

## 对策（本地 Windows）
1. **别用 `/restart`**：在终端跑 `hermes gateway restart`（外部 stop+start，不依赖 watcher）；桌面端用桌面自己的重启
2. 想让 `/restart` 管用：让网关进程带上 `HERMES_GATEWAY_EXTERNAL_SUPERVISOR=1` → 走 exit 75 → 计划任务约 1 分钟内自动拉回（前提：网关确实由计划任务托管）
3. 本地版本若是 v0.18（云上已 v0.21.1），这块逻辑一个月内改过多次，升级也可能解决

## 排查口令（Windows）
```powershell
hermes gateway status
hermes --version
Select-String -Path $env:USERPROFILE\.hermes\logs\gateway.log -Pattern "restart watcher|Detached restart|Exiting with code"
Get-ChildItem $env:USERPROFILE\.hermes\.restart_*.json
```

已同步把这个坑写进 hermes-agent 技能的 `references/windows-quirks.md`。
