"""快速横扫：多币种 x 多周期，看哪条线能赚钱"""
from decimal import Decimal
from pathlib import Path
import yaml
from analysis.report import _extract_equity_curve, _extract_trades
from analysis.metrics import calc_metrics
from backtest.adapter import create_crypto_instrument, kline_to_bar_type
from backtest.runner import BacktestRunner
from data.store import MarketStore

cfg = yaml.safe_load(open("config.yaml"))
store = MarketStore(Path(cfg["store"]["path"]))
bt_cfg = cfg.get("backtest", {})
start = bt_cfg.get("start", "2024-01-01")
end = bt_cfg.get("end")

from strategies.examples.ema_short import EMAShort, EMAShortConfig

# 测试矩阵
tests = [
    # (symbol, tf, fast, slow, label)
    ("BTC/USDT", "15m", 20, 200, "BTC 15m EMA20/200"),
    ("BTC/USDT", "15m", 20, 100, "BTC 15m EMA20/100"),
    ("BTC/USDT", "15m", 50, 200, "BTC 15m EMA50/200"),
    ("BTC/USDT", "1h", 20, 200, "BTC 1h EMA20/200"),
    ("BTC/USDT", "4h", 20, 50, "BTC 4h EMA20/50"),
    ("ETH/USDT", "1h", 20, 200, "ETH 1h EMA20/200"),
    ("SOL/USDT", "1h", 20, 200, "SOL 1h EMA20/200"),
    ("SOL/USDT", "1h", 10, 50, "SOL 1h EMA10/50"),
    ("BNB/USDT", "1h", 20, 200, "BNB 1h EMA20/200"),
    ("DOGE/USDT", "1h", 20, 200, "DOGE 1h EMA20/200"),
]

print(f"{'配置':<22} {'最终权益':>10} {'收益率':>8} {'夏普':>6} {'回撤':>7} {'交易':>5} {'胜率':>6} {'盈亏比':>6} {'K线':>6}")
print("-" * 96)
for symbol, tf, fast, slow, label in tests:
    try:
        instrument = create_crypto_instrument(symbol)
        bar_type = kline_to_bar_type(symbol, "BINANCE", tf)
        strat = EMAShort(EMAShortConfig(instrument_id=instrument.id, bar_type=bar_type, trade_size=Decimal("5"), fast_ema_period=fast, slow_ema_period=slow))
        runner = BacktestRunner(store)
        result = runner.run(symbol, tf, strat, start=start, end=end)
        equity = _extract_equity_curve(result["reports"]["account"])
        trades = _extract_trades(result["reports"]["positions"])
        m = calc_metrics(equity, trades) if not equity.empty else {}
        pf = m.get("profit_factor", 0)
        pf_s = f"{pf:.2f}" if pf != float("inf") and pf not in (0, None) else ("inf" if pf == float("inf") else "0.00")
        bars = result["reports"]["config"]["bars"]
        print(f"{label:<22} ${m.get('final_equity',0):>8.2f} {m.get('total_return_pct',0):>7.2f}% {m.get('sharpe_ratio',0):>5.2f} -{m.get('max_drawdown_pct',0):>5.1f}% {m.get('total_trades',0) or 0:>4d} {m.get('win_rate_pct',0):>5.1f}% {pf_s:>6} {bars:>6d}")
        runner.dispose()
    except Exception as e:
        print(f"{label:<22} ERROR: {e}")

store.close()
print("-" * 96)
