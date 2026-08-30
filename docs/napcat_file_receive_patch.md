# 云上 Hermes 接收 QQ 文件 —— 问题定位与改法

> 适用对象：跑在 Linux 上的云上 Hermes，其 `gateway/platforms/napcat.py` 当前为 683 行版本（无文件接收功能）。
> 目标：让云上 Hermes 能像本机一样，接收 QQ 私聊/群聊发来的文件并落盘。

---

## 一、问题定位（已读源码确认）

云上版 `napcat.py` 通篇读完，相比本机 783 行完整版，**缺失 3 处**：

| # | 缺失内容 | 位置（本机版） | 后果 |
|---|---------|--------------|------|
| 1 | `_file_save_dir()` 函数 | 257-263 行 | 没有落盘目录逻辑，收到文件也没地方写 |
| 2 | `_extract_files()` 函数 | 235-254 行 | 完全不解析 `type=="file"` 的 message 段 |
| 3 | `_process_message` 中的文件处理分支 | 472 行 + 538-588 行 | 文件消息在 500 行 `if not text and not media_urls: return` 处被直接丢弃 |

**关键点**：云上版只处理了 `image`（图片）和 `record`（语音→wav）两种入站媒体，文件（`file`）和视频（`video`）在入站侧全都没解析——所以 QQ 发文件过来，网关当"空消息"扔了。

**注意**：云上版 outbound 已有 `send_document` / `send_video`（能发文件），只是 inbound 不收。是"能发不能收"。

---

## 二、改法（3 步，按顺序做）

### 改法 1：新增 `_file_save_dir()` 函数

**插入位置**：放在云上版 `_extract_record()` 函数（218-222 行）之后、`_extract_reply_id()`（225 行）之前。

**代码**（已改为 Linux 安全路径，不要照抄本机的 `D:/Downloads/qq-files`）：

```python
def _file_save_dir(sender_id: str) -> str:
    """Per-sender daily subdir for received QQ files (Linux-safe)."""
    import os
    base = os.environ.get("HERMES_QQ_FILE_DIR") or os.path.join(
        os.path.expanduser("~"), "qq-files"
    )
    return os.path.join(base, str(sender_id), datetime.now().strftime("%Y%m%d"))
```

> 说明：默认落到 `~/<你的用户>/qq-files/<发送方QQ>/<YYYYMMDD>/`。也可在 `config.yaml` 里加 `extra.qq_file_dir` 覆盖（见改法 3 末尾提示）。

---

### 改法 2：新增 `_extract_files()` 函数

**插入位置**：紧接在改法 1 的 `_file_save_dir()` 之后。

**代码**（直接复制本机版）：

```python
def _extract_files(segments: list[dict]) -> list[dict]:
    """Extract file segments (OneBot type 'file') from a message.

    Private-chat file sends usually carry only ``file_id`` + ``file`` (the
    original filename) and NO ``url`` — those must be resolved via the
    OneBot ``get_file`` API. Group-file shares / forwards may carry a real
    ``url``. We capture both shapes plus size (field name varies).
    """
    result: list[dict] = []
    for s in segments:
        if s.get("type") == "file":
            data = s.get("data", {}) or {}
            result.append({
                "name": data.get("name", ""),
                "file": data.get("file", ""),      # private-chat sends filename here
                "url": data.get("url", ""),
                "file_id": data.get("file_id", ""),
                "size": data.get("size", data.get("file_size", "")),
            })
    return result
```

---

### 改法 3：在 `_process_message` 接入文件段

**3a**：在云上版 `_process_message` 里找到这一行（约 472 行）：
```python
        record_url = _extract_record(segments)
```
在它**正下方**加一行：
```python
        file_segments = _extract_files(segments)
```

**3b**：在云上版 `elif record_url:` 分支结束处（即 `logger.debug("NapCat: voice -> %s", wav)` 那一行之后，约 498 行），**插入整段文件处理代码**：

```python
        # File segment (excel / txt / etc.) — resolve to a local path and
        # surface it as a text marker so the agent can read the file.
        # Only when not already dominated by an image/voice segment.
        if file_segments and not image_urls and not record_url:
            file_info = file_segments[0]
            file_name = file_info.get("file") or file_info.get("name") or "unknown"
            file_url = file_info.get("url", "")
            file_id = file_info.get("file_id", "")
            saved_path: str | None = None
            try:
                if file_url:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(file_url) as resp:
                            resp.raise_for_status()
                            raw = await resp.read()
                    save_dir = _file_save_dir(sender_id)
                    os.makedirs(save_dir, exist_ok=True)
                    dst = os.path.join(save_dir, file_name)
                    with open(dst, "wb") as f:
                        f.write(raw)
                    saved_path = dst
                elif file_id:
                    resp = await call_onebot_api(
                        self._http_api, "get_file",
                        {"file_id": file_id},
                        self._access_token or None,
                    )
                    fd = (resp or {}).get("data", {})
                    src = fd.get("file") or fd.get("url", "")
                    if src and os.path.isfile(src):
                        save_dir = _file_save_dir(sender_id)
                        os.makedirs(save_dir, exist_ok=True)
                        dst = os.path.join(save_dir, file_name)
                        import shutil
                        shutil.copy2(src, dst)
                        saved_path = dst
                    elif fd.get("base64"):
                        import base64
                        raw = base64.b64decode(fd["base64"])
                        save_dir = _file_save_dir(sender_id)
                        os.makedirs(save_dir, exist_ok=True)
                        dst = os.path.join(save_dir, file_name)
                        with open(dst, "wb") as f:
                            f.write(raw)
                        saved_path = dst
            except Exception as exc:
                logger.warning("NapCat: file receive failed for %s: %s", file_name, exc)
            marker = (
                f"[收到文件: {file_name} → {saved_path}]"
                if saved_path
                else f"[收到文件: {file_name} (未能获取内容)]"
            )
            text = (text + "\n" + marker) if text else marker
            logger.info("NapCat: file segment from %s -> %s", sender_id, saved_path or "(failed)")
```

> 依赖说明：`call_onebot_api` 云上版已导入（第 48 行 `from gateway.platforms.napcat_api import (call_onebot_api, ...)`），所以 `get_file` 直接走通用封装即可，不用再单独写封装。

---

## 三、可选增强（非必须）

如果想用 `config.yaml` 指定落盘目录，在 `config.yaml` 的 `platforms.napcat.extra` 里加：
```yaml
          qq_file_dir: "/data/hermes/qq-files"
```
并把改法 1 的 `_file_save_dir` 第一行改成读这个配置（在 `__init__` 里存 `self._qq_file_dir`，函数内优先用）：
```python
    base = getattr(self, "_qq_file_dir", "") or os.environ.get("HERMES_QQ_FILE_DIR") or os.path.join(os.path.expanduser("~"), "qq-files")
```

---

## 四、验证步骤（改完必须跑）

1. 重启 Hermes 网关（让新 `napcat.py` 生效）。
2. 在 QQ 私聊给云上机器人发一个 `.txt` 文件。
3. 检查 `~/<用户>/qq-files/<你的QQ>/<今天日期>/` 目录下是否出现该文件。
4. 确认豆子（agent）收到的消息里包含 `[收到文件: xxx.txt → /路径/xxx.txt]` 标记，且能 `read_file` 读到内容。
5. 若没落盘：查网关日志 `grep "NapCat: file" ` 看是 `file receive failed` 还是根本没进 `_process_message`（后者说明 `file_id`/`url` 字段名跟 NapCat 实际返回不一致，需打印 `segments` 核对）。

---

## 五、常见坑

- **Linux 路径**：本机硬编码 `D:/Downloads/qq-files` 在 Linux 上会创建失败或落到奇怪位置，已改为 `~` 下，务必用改法 1 的 Linux 版。
- **私聊只有 file_id**：QQ 私聊发文件常不带 `url`，必须走 `get_file` API（改法 3b 的 `elif file_id` 分支已覆盖）。
- **群文件**：群聊发文件可能带真实 `url`，走 `if file_url` 分支直接下。
- **大小限制**：受 `media_max_mb`（默认 5MB）约束，超大的文件 `get_file` 返回可能超限，需要时调大配置。
