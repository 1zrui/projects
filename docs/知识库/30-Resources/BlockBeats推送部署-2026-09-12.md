# BlockBeats 快讯推送 · 云上部署完成（2026-09-12）

大哥从 QQ 发来的 `blockbeats-push-20260912.zip`（收到过程见《QQ发文件收不到-代理导致》），已部署在云服务器。

## 部署结果
```
安装目录：/opt/blockbeats-push（代码 + venv + .env + state/logs/cache）
服务：blockbeats-push.service（系统级 systemd，root，已 enable 开机自启）
进程：/opt/blockbeats-push/.venv/bin/python -u blockbeats_listener.py
源：https://www.theblockbeats.info/newsflash/rss（20 秒轮询，直连优先 → BB_PROXY 兜底）
```

## 关键配置（.env，600 root，密钥从 ~/.hermes/.env 取，未经过聊天）
```
QQ_APP_ID=1905595541
QQ_CLIENT_SECRET=（与 Hermes 网关同一个机器人的密钥）
BB_GROUP_OPENID=78BAFCB823704D924249E74E9F5D7850   ← 群 631502972，当前 appid 下的实测值
BB_POLL=20
BB_PROXY=http://127.0.0.1:20171
```
⚠️ **README 里默认的 `8DDF1613...D9201` 是旧 appid 的 openid，直接用会报"群已注销"** —— 必须用网关日志里现抓的那个。

## 验收（三步都过）
1. `--check`：抓取解析 9 条，字体探测到 NotoSansCJK Regular/Bold ✅
2. `--preview`：卡片渲染成功（`cache/preview.png`）✅
3. `--test-send`：`推送图片 id=test 发送=OK` → 群里收到测试卡 ✅
4. 常驻：`systemctl start` → 补推当前页 9 条（`last_max_id` 从 0 起），全部 `发送=OK`，进度落到 `{"last_max_id": 366759}` ✅

## 运维
```bash
systemctl status|start|stop|restart blockbeats-push
journalctl -u blockbeats-push -f          # 或 tail -f /opt/blockbeats-push/logs/listener.log
sudo /opt/blockbeats-push/.venv/bin/python /opt/blockbeats-push/blockbeats_listener.py --check|--preview|--test-send
```
补发历史：改 `state/last_id.json` 里的数字（别调太小，否则补几十条）。

## 注意
- ⚠️ **同一个群只能跑一个实例**：本地 Windows 那个监听器若还在跑，每条快讯会推两遍 → 云上验收通过后要停掉本机那个
- 日志里每条会出现两行（`推送图片 id=..` 来自 `send_qq_image`，`推送 id=..` 来自主循环）→ **只是重复打日志，不是重复发送**
- 发图链路失败会自动降级发全文文字（`[warn] qqbot 图片链路失败`）
