# QQ Bot 文件接收修复

摘要：修复 Hermes qqbot 适配器无法接收 C2C 文件附件的问题，涉及 url_safety 白名单和 aiohttp SSL 配置。

## 问题现象

QQ 私聊发文件（txt/zip 等），日志显示附件被检测到（content_type=file），但文件未下载、agent 收不到。图片正常。

## 根因

两个问题叠加：

1. **url_safety 拦截**：`tools/url_safety.py` 的 `_TRUSTED_PRIVATE_IP_HOSTS` 只有 `multimedia.nt.qq.com.cn`（图片 CDN），缺少 `grouptalk.c2c.qq.com`（C2C 文件下载域名）。文件 URL 解析到 `120.233.50.x` 被当作私有 IP 拦截。

2. **aiohttp SSL 兼容性**：原代码 `TCPConnector(ssl=False)` 在 aiohttp 3.14.3 下不能正确禁用 SSL 验证，导致连接失败。

## 修复内容

### 文件 1：`tools/url_safety.py`

```python
_TRUSTED_PRIVATE_IP_HOSTS = frozenset({
    "multimedia.nt.qq.com.cn",
    "grouptalk.c2c.qq.com",  # QQ Bot C2C file attachment downloads
})
```

### 文件 2：`gateway/platforms/qqbot/adapter.py` `_download_and_cache` 方法

将：
```python
_no_connector = _aiohttp.TCPConnector(ssl=False)
```

改为：
```python
import ssl as _ssl_mod
_ssl_ctx = _ssl_mod.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = _ssl_mod.CERT_NONE
_no_connector = _aiohttp.TCPConnector(ssl=_ssl_ctx)
```

同时将 `resp.content`（StreamReader）改为 `await resp.read()`（bytes），确保数据完整读取。

## 验证

修复后测试：QQ 发送 emappsdj_cookie.txt → 日志显示 status=200, downloaded 2045 bytes → agent 收到 `[file: emappsdj_cookie.txt (/path/to/file)]` → 文件内容可读。

## 注意事项

- 这些补丁直接改了 venv 里的源码，`hermes update --gateway` 会覆盖，更新后需重新打补丁
- 参考 GitHub issue：NousResearch/hermes-agent#47123（url_safety whitelist）、#26399（file path not passed to agent）
