# BSC Meme 监控

## 文件
- `bsc_meme_monitor.py` — 主脚本（纯标准库，零依赖）
- `bsc_config.json` — 配置（阈值/关键词/数据源参数）

## 部署位置
`~/meme-monitor/`

## 数据源
1. **DexScreener** — boosts/profiles 流（推广位精准发现）
2. **GeckoTerminal** — BSC trending pools 分页拉取（量大，5页100+个）
- 两源完全不重叠，合计覆盖120+个BSC币

## 运行方式
```bash
# 常驻循环（3分钟一轮）
nohup python3 bsc_meme_monitor.py --loop >> monitor.log 2>&1 &

# 单次扫描
python3 bsc_meme_monitor.py
```

## QQ群推送
- 用 QQ Bot API（appId/clientSecret → getAppAccessToken）
- 群 openid: `7861772C9D3065DF0986CAE70EF94435`
- 推送逻辑：信号报警合并一条推送，新币入池只记日志不推送
- token endpoint: `https://bots.qq.com/app/getAppAccessToken`（注意不是 getAppToken）
- Authorization header: `QQBot {token}`（不是 Bearer）
- 参考实现: `/opt/blockbeats-push/blockbeats_listener.py`

## 信号类型
| 图标 | 含义 | 默认阈值 | 冷却 |
|------|------|---------|------|
| 🚀 | 5分钟急拉 | ≥+15% | 5分钟 |
| 🔻 | 5分钟急砸 | ≤-15% | 5分钟 |
| 🔥 | 1小时大涨 | ≥+50% | 5分钟 |
| ⚠️ | 流动性骤降（撤池前兆）| ≥-20% | 5分钟 |
| 💥 | 5分钟放量异动 | 超1h均量3倍且>$2000 | 5分钟 |

## 数据文件
| 文件 | 说明 |
|------|------|
| `bsc_events.jsonl` | 全部报警事件（每行一条JSON） |
| `bsc_watch.json` | 盯盘池状态（重启不丢） |
| `monitor.log` | 运行日志 |

## 踩坑
- DexScreener免费API的boosts/profiles流全网才30条，BSC只有5-8个，不能单独用
- GeckoTerminal有429限流，页间sleep 1.5s，最多5-6页
- QQ Bot API直连 `api.binance.com` 会503/451（被墙），`data-api.binance.vision` 可用但那是CEX现货
- `bots.qq.com/app/getAppToken` 返回503，正确endpoint是 `getAppAccessToken`
- 每个新币/信号逐条推送会刷屏，必须合并
- 信号带合约地址（ca变量在scan_once的for循环里就是合约地址）
