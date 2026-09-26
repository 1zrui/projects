---
title: 当贝投影装第三方 APK 排查 & 汽水音乐车机版
date: 2026-09-27
tags: [当贝, 投影, Android, APK, 汽水音乐]
---

# 当贝投影装第三方 APK 排查 & 汽水音乐车机版

## 背景
目标：在**当贝 X9 Max**（当贝OS 6.0 / **Android 14** / 联发科 MT9681 / 4K）上装汽水音乐并正常放歌。

- 手机版（`com.luna.music` v20.3.0，arm64-only，minSdk 21 / targetSdk 30）→ **能装能开，但放不出歌**（疑设备判定）
- 车机版（`com.luna.music.car` v1.0.9，arm64-only，minSdk 24 / targetSdk 30）→ **装不上**，提示「应用未安装，请检查安装包」

## 车机版包信息（已验证）
- 来源直链（沙发管家 CDN，TV 应用市场，下载 12.7 万次）：
  `https://apps2.o.autoshafa.com/apk/com.luna.music.car.2c0df2072d9fb90bd32e4e2c31cbd94b.apk`
  （文件名中的 hash 即该文件 MD5，可作完整性校验）
- 页面：`https://m.shafa.com/apk/qishuiyinyue.html`
- 签名：**字节官方证书 `O=bytedance`**，v1 + v2 签名均存在（`X-Android-APK-Signed: 2`）
- 体积 39,036,739 字节（37.2 MiB），1198 个条目，4 个 dex（格式 `037`）
- 声明 `extractNativeLibs="false"`，36 个 arm64 `.so` **未压缩 + 4096 页对齐**（合规）
- manifest：无 uses-feature 硬依赖；uses-library 仅 androidx.window 且 `required=false`；无 sharedUserId；provider authorities 为 `com.luna.music.car.{TicketGuardProvider,androidx-startup,apm}`

## 已排除的原因（逐项验证过）
| 假设 | 结论 |
|---|---|
| 下载不完整 | ✗ nginx 日志显示 39,036,739 字节全量送达 |
| 签名方案不被 Android 14 接受 | ✗ 有 v2 签名块 |
| zip 结构异常（zipflinger） | ✗ 无 data descriptor，central/local 一致，无重复条目 |
| ABI 不匹配 | ✗ 手机版同为 arm64-only 且能装 → 系统是 64 位 |
| 包名/签名冲突（已卸载干净） | ✗ 用户已卸载全部汽水音乐后仍失败 |
| extractNativeLibs 页对齐问题 | ✗ 已改成 `true` 重新打包签名，仍失败 |
| 包名被系统拉黑 | ✗ 换包名 `com.luna.music.cxr` 重签，仍失败 |
| dex/arsc 格式 | ✗ dex 037 合法、arsc 为标准 RES_TABLE_TYPE |
| manifest 可疑声明 | ✗ 与手机版逐项对比，差异均为「精简版」正常差异 |
| 传输通道（Via 下载 / 文件管理器 / U 盘 / 浏览器） | ✗ 用户 U 盘、文件管理器均试过，同一提示 |

## 同机可用的通道（已知事实）
- **Via 浏览器（第三方 APK）是用 U 盘装成功的** → U 盘侧载通道本身是通的
- 当贝官方文档要求：`设置 → 通用设置/系统设置 → 安全与隐私 → 允许第三方应用安装 / 安装未知来源应用`

## 未解 & 下一步
1. **adb 拿精确错误码**（唯一能定性的一步）：
   - 投影开「开发者选项 → ADB 网络调试」，电脑 `adb connect <IP>:5555` → `adb install -r xxx.apk`
   - 一键工具包（platform-tools + bat + APK）：`http://119.29.238.30/apk/adb-kit.zip`
2. 待试：`当贝市场 → 管理 → 远程推送`（走当贝自家安装通道）
3. 备选思路：若车机版始终装不上，转向解决**手机版「能开不能放」**（登录账号 / 音质改标准 / 音轨输出通道）

## 重打包工具箱（云端已装）
`zipalign` / `apksigner` / `openjdk-21` / `apktool 2.7` / `pyaxmlparser` / `androguard`（venv: `/tmp/apkvenv`）
- 改 AXML 单个字符串（等长替换）与布尔属性（`extractNativeLibs`）的脚本：`/tmp/wp/../combine.py`、`/tmp/patch_axml.py`
- 重打包必须保持 `.so` 为 stored，最后 `zipalign -f -p 4` 再 `apksigner sign`
