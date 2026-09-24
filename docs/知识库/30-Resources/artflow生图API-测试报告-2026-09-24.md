# artflow.vip 生图 API 测试报告（2026-09-24）

大哥给的生图 API，实测可用，出图质量高。**但延迟波动极大（31s ~ 199s），且返回格式不固定
（有时 url 有时 b64_json），写调用代码必须两种都兼容。**

## 接入信息
- **Base URL**：`https://api.artflow.vip/v1`
- **Key**：`~/.config/artflow/key`（勿提交到 git）
- **网关类型**：**New API**（根路径返回 New API 的 SPA 页面）
- **可用模型**（`GET /v1/models` 只有两个）：

| 模型 ID | owned_by | 端点 |
|---|---|---|
| `gpt-image-2.5-flare` | openai | openai |
| `gpt-image-2.5-sunburst` | openai | openai |

## 实测结果（全部 HTTP 200）

| # | 模型 | 提示词 | 尺寸 | 耗时 | 返回 | image_tokens | 文件 |
|---|---|---|---|---|---|---|---|
| 1 | flare | 红苹果静物（英） | 1024x1024 | **30.9s** | **url** | 1650 | 1.62MB |
| 2 | sunburst | 红苹果静物（英） | 1024x1024 | **96.8s** | **b64_json** | 1056 | 1.72MB |
| 3 | flare | 红苹果（英，竖版） | 1024x1536 | **199.1s** | b64_json | 1593 | 2.43MB |
| 4 | flare | 年轻女性正面特写（中） | 1024x1024 | **148.3s** | b64_json | 1076 | 3.39MB |
| 5 | flare | **/v1/images/edits** 把苹果变蓝 | 1024x1024 | **229.9s** | b64_json | 3313 | 2.21MB |
| 6 | flare | 蓝陶瓷杯（英，复测） | 1024x1024 | **>300s（超时掐断）** | 截断 | — | 1.75MB |

**结论**
- ✅ **中文提示词正常工作**（`revised_prompt` 原样回传中文），人物五官/皮肤质感/眼神都没崩
- ✅ **竖版 1024x1536 支持**（输出确认 1024x1536）
- ✅ **`/v1/images/edits` 图片编辑可用**（实测把红苹果改成蓝色，成功，画面其余部分保持不变）
- ⚠️ **返回格式不固定**：同一模型同一尺寸，一次给 `url`、一次给 `b64_json` → 调用方必须兼容两种
- ⚠️⚠️ **延迟极不稳定：31s ~ 300s+**。六次调用实测 30.9 / 96.8 / 199.1 / 148.3 / 229.9 / >300s，
  复测那轮直接超过 300s 被 curl 掐断（响应体已 1.75MB 但仍未收完）。
  **→ 不适合同步等待的前台交互；必须设超时 ≥ 600s 或改异步轮询。**
  **→ 相比之下本地豆包通道（doubao-image-gen）快得多，日常出图优先用它，artflow 作为质量兜底。**

## 出图质量（vision 评估）
- **人物特写（中文提示词）**：✅ **杂志级**。五官比例协调无畸变、直视镜头、柔和自然光立体感强、
  皮肤保留自然纹理（**没有"塑料脸"**）、额头有自然飞发。**这一档完全够大哥的人像需求。**
- **静物（苹果）**：写实度高，但**"过于完美"** —— 果柄光滑笔直不像真实木质、形状接近理想球体，
  有 3D 渲染感。这是 gpt-image 系列的已知特征，不是这个网关的问题。
- **sunburst vs flare**：sunburst 背景元素更丰富（含绿植/窗光/木椅），token 更少（1056 vs 1650），
  但耗时更长（96.8s vs 30.9s）。**flare 更快，sunburst 细节更多。**

## 调用配方（必须兼容 url / b64_json 两种返回）
```python
import json, base64, subprocess

KEY = open(os.path.expanduser("~/.config/artflow/key")).read().strip()
payload = {"model": "gpt-image-2.5-flare",
           "prompt": "…",
           "n": 1, "size": "1024x1024"}
# 必须走 curl 子进程：execute_code 沙箱无网
r = subprocess.run(["curl", "-s", "-m", "300", "-X", "POST",
                    "https://api.artflow.vip/v1/images/generations",
                    "-H", f"Authorization: Bearer {KEY}",
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps(payload, ensure_ascii=False)],
                   capture_output=True, text=True)
d = json.loads(r.stdout)["data"][0]
if "b64_json" in d:
    open("out.png", "wb").write(base64.b64decode(d["b64_json"]))
else:
    subprocess.run(["curl", "-s", "-m", "180", "-o", "out.png", d["url"]])
```
- **URL 有效期未知** —— 拿到 url 要**立刻下载落盘**，别存 url 当结果
- URL 域名是 `v4-gateway-v2.shagentai.com`（中转，非 artflow 本身）

## 待确认
- `/v1/images/edits`（图片编辑）是否支持 —— 首次测试超时未完成
- 速率限制 / 并发上限
- 计费（网关后台可查，本次只看到 token 用量）
- 是否支持 `n>1`、`quality`、`style` 等参数

## 相关
- 本地已有的生图通道：[[doubao-image-gen]]（豆包，CDP 驱动）、ComfyUI
