# nautilus_trader 1.231.0 API 陷阱实录

## 1. 环境：PYTHONPATH 污染

Hermes Agent 运行时会设置 `PYTHONPATH=D:\Hermes\hermes-agent;D:\Hermes\hermes-agent\venv\Lib\site-packages`，其中 numpy 是 Python 3.11 编译版，与项目 venv（Python 3.13）冲突。

**错误**：
```
ModuleNotFoundError: No module named 'numpy._core._multiarray_umath'
```

**修复**：每次运行项目代码前清空 PYTHONPATH
```bash
PYTHONPATH="" uv run python main.py sync
```

---

## 2. 交易品种：用 CurrencyPair，不是 Instrument

```python
# ❌ 错误
from nautilus_trader.model.instruments import Instrument
Instrument(instrument_id=..., base_currency=..., price_increment=Decimal("0.01"), ...)

# ✅ 正确
from nautilus_trader.model.instruments.currency_pair import CurrencyPair
from nautilus_trader.model.objects import Price, Quantity

CurrencyPair(
    instrument_id=InstrumentId(Symbol("BTCUSDT"), Venue("BINANCE")),
    raw_symbol=Symbol("BTCUSDT"),
    base_currency=BTC,
    quote_currency=USDT,
    price_precision=2,
    size_precision=6,
    price_increment=Price(1, 2),           # 0.01
    size_increment=Quantity(1, 6),         # 0.000001
    margin_init=Decimal("0.05"),
    margin_maint=Decimal("0.025"),
    maker_fee=Decimal("0.001"),
    taker_fee=Decimal("0.001"),
    ts_event=0,
    ts_init=0,
)
```

**错误**：`TypeError: __init__() got an unexpected keyword argument 'base_currency'`（Instrument 没有 base_currency 参数）
**错误**：`TypeError: Argument 'price_increment' has incorrect type (expected nautilus_trader.model.objects.Price, got decimal.Decimal)`（Price 不是 Decimal）

---

## 3. BarDataWrangler.process(df) 列约束

```python
from nautilus_trader.persistence.wranglers import BarDataWrangler

# ✅ 正确：timestamp 必须是 DataFrame 索引（UTC tz-aware）
#         只保留 [open, high, low, close, volume] 列
bar_cols = ["open", "high", "low", "close"]
if "volume" in df.columns:
    bar_cols.append("volume")
df_out = df[bar_cols].copy()
df_out.index = df["timestamp"].copy()
df_out.index.name = "timestamp"
# 确保底层数组可写
for col in df_out.columns:
    df_out[col] = df_out[col].values.copy()

wrangler = BarDataWrangler(bar_type=bar_type, instrument=instrument)
bars = wrangler.process(df_out)
```

**错误 1**：`AttributeError: 'RangeIndex' object has no attribute 'tzinfo'` — timestamp 不是索引
**错误 2**：`ValueError: Buffer dtype mismatch, expected 'double' but got Python object` — 有多余列（symbol/timeframe 等字符串列）
**错误 3**：`ValueError: buffer source array is read-only` — 底层 numpy 数组不可写，需 `.values.copy()`

---

## 4. cache.price() 需要两个参数

```python
# ❌ 错误
price = self.cache.price(self.config.instrument_id)

# ✅ 正确
from nautilus_trader.model.enums import PriceType
price = self.cache.price(self.config.instrument_id, PriceType.LAST)
```

**错误**：`TypeError: price() takes exactly 2 positional arguments (1 given)`

---

## 5. 不要重写 close_position

`Strategy` 父类有带参的 `close_position(self, instrument_id, side, ...)` 方法。重写为无参版会导致 `close_all_positions` 调用时崩溃。

```python
# ❌ 错误 — 命名冲突
def close_position(self):
    self.close_all_positions(self.config.instrument_id)

# ✅ 正确 — 改名
def flat(self):
    self.close_all_positions(self.config.instrument_id)
```

**错误**：`TypeError: QuantStrategy.close_position() takes 1 positional argument but 8 were given`

---

## 6. self.config 是只读属性

```python
# ❌ 错误 — 不可写
def __init__(self, config):
    super().__init__(config)
    self.config = config

# ✅ 正确 — 父类 __init__ 已经设好了
def __init__(self, config):
    super().__init__(config)
```

**错误**：`AttributeError: attribute 'config' of 'nautilus_trader.common.actor.Actor' objects is not writable`

---

## 7. 仓位语义：名义金额 vs 数量

**现货 CASH 账户**：`trade_size` 应该是 USDT 名义金额，不是币数量。

```python
def buy_market(self, notional: Decimal | None = None):
    instrument = self.cache.instrument(self.config.instrument_id)
    price = self.cache.price(self.config.instrument_id, PriceType.LAST)
    if price is None:
        return
    trade_val = notional or self.config.trade_size
    qty = instrument.make_qty(trade_val / price)  # ← 关键：金额/价格=数量
    order = self.order_factory.market(
        self.config.instrument_id, OrderSide.BUY, qty,
    )
    self.submit_order(order)
```

**错误**：`AccountBalanceNegative(balance=-2058307.56132, currency=USDT)` — trade_size=100 被当作 100 BTC 买入，$10,000 本金直接爆仓。

---

## 8. 现货 CASH 账户不能做空

`AccountType.CASH`（现货）只能做多。策略做空信号只能平仓，不能开空仓。

**EMA 策略（正确版）**：
```python
def on_bar(self, bar: Bar):
    if not self.indicators_initialized():
        return
    fast = self.fast_ema.value
    slow = self.slow_ema.value
    if fast >= slow and self.is_flat():
        self.buy_market()          # 多头信号 + 无持仓 → 买入
    elif fast < slow and not self.is_flat():
        self.flat()                # 空头信号 + 有持仓 → 平仓（不做空）
```

---

## 9. BacktestEngine 低层 API 用法

```python
from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money

engine = BacktestEngine(
    config=BacktestEngineConfig(
        logging=LoggingConfig(log_level="ERROR"),
    ),
)

BINANCE = Venue("BINANCE")
engine.add_venue(
    venue=BINANCE,
    oms_type=OmsType.NETTING,
    account_type=AccountType.CASH,              # 现货
    base_currency=None,                         # 多币种账户
    starting_balances=[Money(Decimal("10000"), USDT)],
)

engine.add_instrument(instrument)
engine.add_data(bars)
engine.add_strategy(strategy)
engine.run()

# 报告
engine.trader.generate_account_report(BINANCE)
engine.trader.generate_positions_report()
engine.trader.generate_order_fills_report()

# 清理
engine.dispose()
```

---

## 10. 多次回测

- 一个进程只能建一个 `BacktestEngine`，第二次建会冲突（全局单例）
- 批量回测策略时必须 `engine.dispose()` 再建新的
- 单引擎重复跑用 `engine.reset()`