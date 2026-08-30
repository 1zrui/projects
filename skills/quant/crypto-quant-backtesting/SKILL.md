---
name: crypto-quant-backtesting
description: 构建加密货币量化回测平台 —— 币安数据源 + DuckDB 存储 + nautilus_trader 事件驱动引擎。覆盖项目架构、数据管道、nautilus_trader API 关键陷阱、仓位语义、HTML 报告生成。项目位于 D:\Hermes\workspace\quant-trader\。
---

# 加密量化回测平台

## 触发条件
- 用户提到量化/回测/策略/选币/回测报告
- 需要操作 `D:\Hermes\workspace\quant-trader\` 项目
- 写新策略、拉币安历史数据、跑回测、看绩效指标

## 平台架构（已建成，勿推倒重来）

```
quant-trader/
├── data/           # collector（ccxt拉币安K线）+ store（DuckDB）+ pipeline（校验/增量）
├── strategies/     # base.py（QuantStrategy基类）+ examples/（EMA等示例）
├── backtest/       # adapter.py（CurrencyPair工厂/Bars转换）+ runner.py（BacktestEngine编排）
├── analysis/       # metrics.py（夏普/回撤/胜率）+ report.py（Plotly HTML报告）
├── main.py         # CLI: sync/update/run/status/quality
└── config.yaml     # 交易对、粒度、回测区间/资金/手续费
```

## 运行铁律

1. **必须用干净环境**：Hermes 的 `PYTHONPATH` 指向 hermes-agent venv（numpy 是 3.11 版），会与项目 venv 撞车。
   ```bash
   cd /d/Hermes/workspace/quant-trader && PYTHONPATH="" uv run python main.py sync
   ```
   漏掉 `PYTHONPATH=""` 会报 `No module named 'numpy._core._multiarray_umath'`。
2. 环境要求：Python 3.12+（本机 3.13.12 可用），`uv sync` 已建 .venv，48 个依赖装好。
3. 已有示例策略走 `backtest/adapter.create_crypto_instrument` + `kline_to_bar_type` 拿 instrument/bar_type 再组策略 config。

## 标准工作流

1. **拉数据**：`python main.py sync`（全量）或 `update`（增量，从本地最新时间戳续拉）
2. **查数据**：`python main.py status` / `quality`
3. **写策略**：继承 `strategies.base.QuantStrategy`，配置继承 `QuantStrategyConfig`（必填 `instrument_id`），实现 `on_start` + `on_bar`。**现货 CASH 账户只能做多**——信号反转时平仓，不做空。
4. **跑回测**：`runner.run(symbol, timeframe, strategy, start, end)` → `generate_html_report(result)` 输出 reports/ 下 HTML
5. **验收**：跑 `scripts/verify_e2e.py`（合成数据全链路）确认无回归

## 关键陷阱（nautilus_trader 1.231.0，详见 references/nautilus-trader-api-pitfalls.md）

- 构造品种用 `CurrencyPair`，不是 `Instrument`；价/量步进要用 `Price(v, prec)` / `Quantity(v, prec)`，不是 Decimal
- `BarDataWrangler.process(df)`：df 索引必须是 UTC timestamp；只留 [open, high, low, close, volume] 列，多余列直接报 dtype/buffer 错
- `cache.price(instrument_id, PriceType.LAST)` 要两个位置参数
- **不要重写 `close_position`**（父类 Strategy 有带参同名方法会崩），平仓助手命名为 `flat()`
- `self.config` 是只读属性，子类不能重赋值
- 仓位语义：`trade_size` 是 USDT 名义金额，`buy_market()` 里用 `qty = notional / cache.price(...)` 换算；按数量下单会直接爆仓（AccountBalanceNegative）
- 引擎一次进程只建一个，批量回测要 `dispose()` 后再跑下一个

## 支持文件
- `references/nautilus-trader-api-pitfalls.md` — 全部 API 陷阱的错误原文 + 修复代码，开发策略时必查