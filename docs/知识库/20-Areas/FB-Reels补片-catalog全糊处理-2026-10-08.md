# FB Reels 2号池 · catalog 顶替全糊的处理（2026-10-08）

> 摘要：fb2 补片时 catalog 顶替候选按播放量取前12条全是 360p/540p 糊片（门槛720p），一条没发出去。改用 `oneshot_topup2.py` 随机打乱+`yt-dlp -F` 只探分辨率不下载，探2条就中2条 1080p。教训：顶替别按播放量排序（高播放老片多为低清），随机更快更准。

## 现象
大哥说「fb2 再补俩视频」，正常跑 `cron_fb_reels_pool2.py`（强制 `_is_catalog_slot=True`）：

```
[顶替] 没有新视频，从 catalog 挑 2 条顶替
[顶替] 已排除已发池 82 条
[顶替] 候选（按播放量）: 12 条备选
[skip-糊] 12 条全是 360p / 540p（门槛 720p）→ 逐个换下一条
```
结果：**一条都没发出去**。回执推群只有「无新视频 / catalog顶替」。
原因：顶替候选是**按播放量排序取前 12 条**，而 FB 上高播放量的老片普遍只有 360p —— 画质闸（`MIN_SIDE=720`）全挡住。

## 处理：一次性脚本 oneshot_topup2.py
路径 `/opt/fb-reels/scripts/oneshot_topup2.py`，用法：

```bash
cd /opt/fb-reels/scripts
/opt/fb-reels/.venv/bin/python oneshot_topup2.py 2    # 补 2 条
```
（后台跑 + notify，别同步等，会占死 QQ 通道）

逻辑：
1. 读 `data/fb2_reels_catalog.csv`，筛时长 8~40s，排除 `last_sent_reel_ids` + `fb2_sent_pool.txt` + `skipped_reel_ids` → 本次可用候选 **616 条**
2. **`random.shuffle` 打乱**（关键：不按播放量，按播放量必踩糊片）
3. 逐条 `yt-dlp -F` **只探分辨率、不下载**（约 3 秒/条），解析 `(\d{3,4})x(\d{3,4})` 取 `min(w,h)` 最大值；只列 `sd` 的返回 0 = 糊
4. ≥720p 的才走 `p2._fetch_and_send()`（下载 → 画质闸 → H.265 转码 → 发群）
5. 收尾 `p2._record("last_sent_reel_ids", ids)` + `p2._archive_and_clean()`，并推一条简短回执

## 实测结果
随机顺序**探 2 条就中 2 条**：`1072422904870143`(12s/1080p)、`1553193303172781`(31s/1080p)，都进了群 624127517，耗时约 1 分钟。

## 教训
- 顶替候选「按播放量取前 N」是糊片重灾区；**随机比按播放量更快更准**。
- 别为了省几秒去改生产脚本的 `candidates[:12]`（改生产脚本先问大哥）。
- 探测比下载省时间：`yt-dlp -F` 3 秒/条，直接下载再 ffprobe 判断会白下高清片。
