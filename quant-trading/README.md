# 加密货币量化回测系统

## 项目结构

```
quant-trading/
├── config.py           # 配置文件
├── data_fetcher.py     # 数据采集 (ccxt + 币安)
├── backtest_engine.py  # 回测引擎 (vectorbt)
├── strategies/         # 策略模块
│   └── __init__.py     # 多因子动量策略 + 双均线策略
├── main.py             # 主入口
├── data/               # K线数据存储
└── utils/              # 工具函数
```

## 快速开始

```bash
# 激活环境
source venv/bin/activate

# 拉取数据 + 回测
python main.py --symbol BTC/USDT --fetch

# 只回测 (使用已保存数据)
python main.py --symbol BTC/USDT

# 对比两种策略
python main.py --compare

# 拉取ETH数据
python main.py --symbol ETH/USDT --fetch
```

## 策略说明

### 1. 多因子动量策略 (默认)
- **买入条件**: RSI<30 + MACD金叉 + 成交量放大1.2倍
- **卖出条件**: RSI>70 或 MACD死叉

### 2. 双均线交叉策略
- **买入**: MA5 上穿 MA20
- **卖出**: MA5 下穿 MA20

## 回测指标

- 总收益率 / 年化收益率
- 最大回撤
- 夏普比率 / Sortino比率
- 胜率 / 盈亏比
- 交易次数 / 平均持仓时间

## 与 NautilusTrader 对接

策略验证通过后，将信号逻辑迁移到本地 NautilusTrader 实盘执行。
