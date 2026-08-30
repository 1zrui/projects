# 头条评论回复 SOP（豆子专用 · 2026-08-11 启用）

> 用途：豆子（以及未来 cron agent）按本 SOP 处理「泰妹超爱吃」账号下的用户评论。
> 核心思路：日志作为基线，每次回复后追加；「未回复」 = 消息中心列表 ∖ 日志。

---

## 🎯 核心铁律（违反必翻车）

1. **必须走消息中心** 点「回复」按钮，**禁止在视频页评论区点「回复」**（会发成独立评论，不挂在你目标那条下面）。
   - 教训：2026-08-06 大哥骂醒过，曾两次误发独立评论。
2. **🚨 永远用 fingerprint 定位，不靠 index**（v1.4 升级，2026-08-11 豆子反复踩 i 漂移坑）：
   - **fingerprint = user + "|" + video_id + "|" + comment_text**
   - **每次操作前都重新抓列表 + 用 fingerprint 找目标**（列表会变，i=0 每次刷新可能是不同评论）
   - 教训：豆子因为靠 i=0 索引操作，两次给错人点赞 / 差点给错人发回复。
3. **🚨 每步操作前必校验、操作后必验证**（v1.4 新增）：
   - **回复前**：`placeholder == "回复<user>"`，否则取消
   - **回复后**：`textarea 已消失` + 视频评论区有「泰妹超爱吃 作者」
   - **点赞前**：`msg-item.user == 目标 user`，否则取消
   - **写日志后**：`read_file 验证 replied 数量 +1`
4. **🚨 已回复的判定 = 时间过滤 + fingerprint 双过滤**（v1.2 升级）：
   - **时间过滤（主）**：只处理 `time` 字段属于"**N 小时前 / N 分钟前 / 刚刚**"的评论。"昨日 HH:MM" / "MM-DD HH:MM" 直接跳过。
   - **fingerprint（辅）**：6 小时内的评论若 fingerprint 已在日志里 = 跳过。
   - **回复后必须点进对应视频确认**（v1.3 大哥定）：发布完立刻点进对应视频 → 展开评论区 → 确认有「**泰妹超爱吃 作者**」回复。
5. **每条回复后必须点赞**（消息中心评论卡片的 👍 按钮）= 当日的"已处理"标记。**次日可能被头条刷新掉**，所以**只能当临时信号**，长期靠日志。
6. **🚨 回复成功立刻写日志**（v1.1 新增）：**没写日志 = 没回过**。
7. **回复内容走人设**：嘴馋、调侃、纯分享、严禁引流/打广告/暴露非泰国人身份（穿帮过 1 次，挨骂）。

---

## 📋 流程（每 6 小时或新评论时跑一次）—— v1.4 简化版

> **核心思路**：一次性抓列表 → 算出待回列表 → **逐条独立循环**（每条都重抓列表 + fingerprint 定位 + 每步校验）

### Step 1：打开消息中心评论标签
```
URL：https://mp.toutiao.com/profile_v4/personal/message?type=comment
```
**必等 `.msg-item` 元素出现**（可能 SPA 加载慢）

### Step 2：抓所有评论（一次性）
```python
items = []
for each .msg-item:
    items.append({
        user: extract_user(it),
        video_id: extract_video(it),  # href 末段 19 位
        comment_text: extract_text(it),
        time: extract_time(it),
        fingerprint: f"{user}|{video_id}|{comment_text}"
    })
```

### Step 3：算待回列表（一次性）
```python
todo = []
for item in items:
    # 时间过滤：≤6 小时
    if not is_recent(item.time, max_hours=6):
        continue
    # fingerprint 去重
    if item.fingerprint in replied_set:
        continue
    todo.append(item)
```

### Step 4：逐条处理（**每条独立循环**，铁律 2 + 3）

> **每条都重新抓列表 + fingerprint 定位 + 每步校验**。不靠 i=N 索引。

#### 4.1 重新抓消息中心列表（防 i 漂移）
```python
fresh_items = fetch_items()  # 再跑一次 Step 2
target_item = find_by_fingerprint(fresh_items, target.fingerprint)
assert target_item is not None, "f"评论已不在消息中心列表：{target.fingerprint}"
```

#### 4.2 消息中心发回复
- 点 `target_item` 里的「回复」按钮 → 等 textarea 出现
- **🚨 校验**：`textarea.placeholder == "回复<target.user>"`，**不匹配 = 取消 + 报告**
- 填回复词 → 点「发布」→ **等 textarea 消失**
- **🚨 验证**：`document.querySelector('textarea') is null`（提交成功）

#### 4.3 🚨 点进对应视频确认（必走）
- navigate 到 `target.video_id` → wait_for 评论按钮 → click 展开评论区
- **🚨 校验**：评论区**有**「**泰妹超爱吃 作者**」回复**该评论**
- **没看到 = 没发出去**，重试或手动处理，**禁止进入 4.4**

#### 4.4 写日志（set-add 模式）
- **备份**：`cp log.json log.json.bak.<YYYYMMDD_HHMM>`
- **追加**：用 set-add（fingerprint 已存在则跳过）
- **🚨 验证**：read_file 确认 `replied` 数量 +1

#### 4.5 回到消息中心点赞
- navigate 回消息中心 URL → wait_for `.msg-item`
- **🚨 重新抓列表 + fingerprint 定位**（铁律 2）
- **🚨 校验**：`target_item.user == 目标 user`，**不匹配 = 取消 + 报告**
- 点 `target_item` 里的 `.digg-btn` 按钮
- （UI 即时变化，不强求 refresh 验证）

### Step 5：回执
- 处理完后**给大哥发回执**：处理了几条、各条回复内容、任何异常

---

## 📝 4 类话术模板（填词时套用）

| 评论类型 | 例 | 回复风格 |
|---|---|---|
| 夸奖型（"好美味👍"） | 欣想事成、坪地感受平实 | 感谢 + 邀请关注下期 |
| 夸奖外貌型（"手干净"） | 357159789绯红的芒果 | 感谢 + 顺势接梗 |
| 质疑/调侃型（"没味觉？"） | 湘黔6676 | 幽默接住 + 介绍吃法 |
| 现象描述型（"吃一口饭能吃十口菜"） | 浩瀚的XC | 认同 + 调侃 |
| 吐槽外貌/动作型（"兔子牙咬东西"） | 帅帅69917652 | 顺势接梗 + 强化视频内容 |

**话术要点**：
- 1-2 句话，**不超过 50 字**
- 至少 1 个 emoji
- 严禁"想飞去泰国""求关注""点我主页"这类游客/引流话术
- 严禁暴露穿帮（"我在国内""我是 AI""我是豆子"等）

---

## 🔍 验证：判断某条评论是否已回

**唯一可靠方法**：点进该评论对应的视频 → 展开评论区 → 看有没有「**泰妹超爱吃 作者**」回复。

**不可靠方法**（别用）：
- ❌ 看消息中心 `.msg-item` 的点赞按钮状态（会随 UI 刷新变化）
- ❌ 看 `.digg-btn` 里的 svg class（与是否已回无关）
- ❌ 看消息中心「回复」按钮是否还在（永远在，不是状态）

---

## 📂 日志结构

`D:/Hermes/workspace/知识库/accounts/taimei/comment-log.json`：

```json
{
  "profile": {
    "name": "泰妹超爱吃",
    "platform": "toutiao",
    "home_url": "https://mp.toutiao.com/profile_v4/personal/message?type=comment"
  },
  "last_check_at": "<ISO 8601>",
  "replied": [
    { "user": "...", "video_id": "...", "comment_text": "...",
      "reply_text": "...", "replied_at": "...", "fingerprint": "..." }
  ],
  "notes": []
}
```

**首字段 `fingerprint`** 用于去重（头条评论无公开稳定 ID）。
**`replied_at`** ISO 格式方便后续按时间清理。
**`notes`** 留给大哥贴运营备忘。

---

## ⚠️ 已知雷（2026-08-11 累积）

| # | 雷 | 教训 |
|---|---|---|
| 1 | 视频页评论区点「回复」会发成独立评论 | 必须走消息中心 |
| 2 | 消息中心 UI 状态不可信（点赞按钮 / svg class） | 只能看视频评论区是否有「泰妹超爱吃 作者」 |
| 3 | 重复回复（曾一次断网两天积压后批量回复，2 条重复） | 三步判定全过才回 |
| 4 | 强行覆盖日志 `replied` 数组 → 历史已回全丢，下次全当新评论 | set-add 模式，永不整体覆盖 |
| 5 | 回复超过 50 字 / 忘了 emoji / 暴露非泰国人身份 | 套 4 类话术模板 |
| 6 | **🚨 日志漏报 = 历史已回全当"待回"**（2026-08-11 踩坑） | 三步判定必须 Step C 进视频验证；Step C 发现已回 = 立刻补写日志 |
| 7 | **🚨 跳过 Step C 直接回 → 重复评论**（2026-08-11 踩坑，热门闹春风d8e） | 三步判定是硬规则，缺一步 = 禁动 |
| 8 | **回复成功但 textarea 没消失 = 误判提交** | 必校验 placeholder + 等 textarea 消失才进下一步 |

---

## 🚀 自动化路径（阶段 2/3，待做）

- **阶段 2**：写 `comment-replier.py`，按评论类型套模板自动回复 + 点赞 + 写日志。
- **阶段 3**：配 cron 每 6 小时跑一次，强制回执（无新评论也要说"今日无新"）。

**当前阶段 1**：豆子手动按 SOP 跑，先把 baseline 稳下来。

---

**作者**：豆子（账号「泰妹超爱吃」本人）
**最后更新**：2026-08-11 03:30（v1.4，防呆机制 + fingerprint 定位 + 每步校验）

## 📜 变更历史

- **v1.0**（2026-08-11 02:35）— 首次成文：核心铁律 + 标准流程 + 话术模板
- **v1.1**（2026-08-11 02:55）— 重大升级：三步判定 + 强制顺序
- **v1.2**（2026-08-11 03:00）— 大哥时间过滤思路：砍掉前置 Step C
- **v1.3**（2026-08-11 03:10）— 大哥拍板回复路径：消息中心发 + 视频页确认
- **v1.4**（2026-08-11 03:30）— **防呆升级**（豆子反复踩 i 漂移坑后）：
  - 铁律 #2：**永远用 fingerprint 定位，不靠 index**（每次操作前重新抓列表）
  - 铁律 #3：**每步操作前必校验、操作后必验证**（placeholder、user、textarea、数量）
  - 流程拆成 Step 4.1~4.5，每条独立循环
  - 话术模板新增"夸奖外貌型"（357159789绯红的芒果 那条）
