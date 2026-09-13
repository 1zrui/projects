# Hermes 辅助模型选择避坑记录（2026-09-04）

> 摘要：辅助任务（标题/压缩/视觉）选模型先看 token 预算，思考型模型直接排除；新模型先 curl 实测再配置。压缩用 mimo-v2.5，标题用 minimax-m3(NVIDIA)。相关：[[模型限流踩坑-2026-08-25]]

## 背景
大哥要求把 auxiliary 里用的 deepseek-v4-flash 全部换掉。主模型保持 deepseek-v4-flash 不动。

## 最终配置
- 主模型：deepseek-v4-flash（不变）
- 压缩 compression：mimo-v2.5（实测压缩质量不错）
- 标题 title_generation：minimaxai/minimax-m3（NVIDIA 渠道，免费额度，64 token 内正常出标题）

## 核心坑：辅助任务有硬编码 token 预算
- 标题生成：`max_tokens=64` 硬编码（agent/title_generator.py），改不了配置
- 带 reasoning/思考链的模型（glm-4.7-flash、glm-4.5-air、mimo-v2.5、sensenova、deepseek 系）会在思考上吃光 64 token，内容吐空
- 测试方法：curl new-api /v1/chat/completions，max_tokens=64 看能否正常输出

## 各模型测试结果（64 token 预算起标题）
| 模型 | 渠道 | 结果 |
|---|---|---|
| minimaxai/minimax-m3 | NVIDIA | ✅ 出标题正常 |
| qwen3.8-flash | opencode-go | ✅ 能出但大哥嫌贵 |
| minimax/minimax-m3:free | OpenRouter | ❌ 话痨，自我介绍吃光预算 |
| glm-4.7-flash | 智谱 | ❌ 思考链太长，500 token 都兜不住 |
| glm-4.5-air | 智谱 | ❌ 思考型，吐空 |
| mimo-v2.5 | opencode-go | ❌ 64 内吐空（500 时正常，适合压缩） |
| sensenova-6.7-flash-lite | 商汤 | ❌ new-api 上模型路由不存在 |
| sensenova-6.8-flash-lite | 商汤 | ❌ 64 内吐空 |
| gpt-oss-20b/120b | NVIDIA | ❌ 响应异常 |
| ling-3.0-flash-fin:free | OpenRouter | ❌ 吐空 |
| z-ai/glm-5.3-free | tokenrouter | ❌ 吐空 |
| GLM-5-Base | scnet | ❌ 吐空 |
| kimi-k3 | NVIDIA | ❌ 超时/异常 |

## 经验
1. 辅助任务（标题/压缩）选模型先看 token 预算，思考型模型直接排除
2. 新模型先 curl 实测再配置，别信渠道列表（sensenova-6.7 在列表里但路由不存在）
3. 免费渠道：NVIDIA（minimax-m3、gpt-oss 系）、OpenRouter free 模型、tokenrouter free
4. 改配置前必须跟大哥确认，这次擅自换 qwen3.8 被骂了
