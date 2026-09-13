# OpenCode Go 排行榜抓取修复记录（2026-09-04）

## 脚本
- cron 调用：`~/.hermes/scripts/fetch_ranking.py`（no_agent 模式，每天 9:00）
- 输出：`/home/ubuntu/workspace/opencode-ranking/latest.json` + `latest.txt`
- 历史：`/home/ubuntu/workspace/opencode-ranking/history.jsonl` 追加写入
- 工作区旧版：`/home/ubuntu/workspace/opencode-ranking/fetch_ranking.py`（注意跟 cron 版不同）

## 根因
页面 8/30 后改版，排行数据从纯 HTML span 搬到 SVG 图表 + pills 结构。旧正则：
```python
<span\s+data-value>   # 要求 data-value 是 span 的第一个属性
```
新页面结构：`<span data-hk="0000..." data-value>110</span>`——data-hk 插到前面，正则匹配失败。

## 修复
```python
# 旧（挂）
<span\s+data-value>([^<]+)</span><span\s+data-name>([^<]+)</span>

# 新（通）
data-value[^>]*>([^<]+)</span>.*?data-name>([^<]+)</span>
```
关键改动：去掉 `<span` 前缀限制，直接用 `data-value[^>]*>` 匹配，不依赖属性顺序。

## 新页面结构要点
- SVG bars 区：`<rect data-animate="bar" data-model="xxx" width="...">` —— 纯视觉，无数值
- Pills 区：`<span data-item data-kind="go" data-model="xxx">` 里有 `<span data-value>NUM</span><span data-name>NAME</span>` —— 这才是真数据
- 中间有 `<span data-label><!--$--><span data-hk="..." data-value>` 嵌套结构
- 直连无需代理（2026-09 实测 HTTP 200，46KB）

## 教训
1. 页面正则写宽松：用 `[^>]*` 而非 `\s`，不依赖属性顺序
2. cron 用的脚本路径是 `~/.hermes/scripts/`，跟工作区副本是不同文件，改完记得两个都更新或确认哪个是真正在用的
3. 抓取失败后检查：curl 返回 200 且有 data-model ≠ 数据能解析成功
4. 排行榜数据格式会随网站改版变化，发现抓取失败先查页面结构再怀疑网络
