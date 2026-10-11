# FongMi 影视TV（TVBox 系）· 免费看全网影视方案

来源：2026-10-11 大哥要「橘汁终身会员」，给替代方案时整理。

## 结论
- **橘汁没有官方终身会员**。网上"永久会员版"= 第三方拆包改的破解 apk，官方版自己都报 `a.gray.BulimiaTGen.a` / `a.gray.Sniffvipvedio`，不值得装。
- 正确解：**FongMi 影视TV**（TVBox 系，GitHub 开源，无广告无会员，片源远多于橘汁）。

## APK 下载
仓库：`github.com/FongMi/Release`（apk 发布在这里，不在 FongMi/TV 仓库）

```
https://github.com/FongMi/Release/releases/download/<版本>/mobile-arm64_v8a.apk     # 手机版
https://github.com/FongMi/Release/releases/download/<版本>/leanback-arm64_v8a.apk   # 电视/盒子版
```
- 另有 `*-armeabi_v7a.apk`（32 位老设备用）
- 版本查法：`curl -s https://github.com/FongMi/Release/releases.atom`
- 2026-10-11 实测版本 5.7.2，两包各约 68MB

## 配置源（关键）
装好后：**设置 → 配置地址 → 粘贴以下地址**

主源（298 个片源 + 直播，高天流云）：
```
https://ghproxy.net/raw.githubusercontent.com/gaotianliuyun/gao/master/js.json
```
备份源：
```
https://ghproxy.net/https://raw.githubusercontent.com/yw88075/tvbox/main/yw.json
https://dxawi.github.io/0/0.json
https://raw.gitcode.com/yydg/ggdx/raw/main/Xboxb.json
```

## 踩坑
- **别用 jsdelivr 的地址**（`cdn.jsdelivr.net/gh/gaotianliuyun/gao@master/js.json`）：
  json 能取到（200），但同仓的 spider jar（`jar/pg.jar`）在 jsdelivr 上返回 **403**，
  导致所有站点加载失败 → 必须走 `ghproxy.net` 或原始 raw 地址。
- TVBox 配置里的 `spider` 是相对路径（`./jar/pg.jar`），由客户端按配置 URL 自动解析，
  所以配置地址用什么域名，jar 就跟着从哪取。
- 接口地址失效很快，一般 1~3 个月换一批。挑源方法：批量 curl 测 200 + 内容含 `sites`/`spider`。

## 接口测活小脚本
```python
import urllib.request, ssl
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
req = urllib.request.Request(url, headers={'User-Agent':'okhttp/3.15'})
raw = urllib.request.urlopen(req, timeout=12, context=ctx).read().decode('utf-8','ignore')
# 单仓: json 里 sites 数量；多仓 TXT: 每行一个接口地址
```
