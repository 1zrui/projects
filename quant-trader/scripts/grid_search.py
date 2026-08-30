"""参数寻优 —— 网格搜索"""
import itertools
from decimal import Decimal
from pathlib import Path
import yaml

from analysis.report import _extract_equity_curve, _extract_trades
from analysis.metrics import calc_metrics
from backtest.adapter import create_crypto_instrument, kline_to_bar_type
from backtest.runner import BacktestRunner
from data.store import MarketStore
from strategies.examples.ema_short import EMAShort, EMAShortConfig
from strategies.examples.rsi_strategy import RSIConfig, RSIStrategy

cfg = yaml.safe_load(open("config.yaml"))
store = MarketStore(Path(cfg["store"]["path"]))
symbol = "BTC/USDT"
timeframe = "1h"
instrument = create_crypto_instrument(symbol)
bar_type = kline_to_bar_type(symbol, "BINANCE", timeframe)
bt_cfg = cfg.get("backtest", {})
start = bt_cfg.get("start", "2024-01-01")
end = bt_cfg.get("end")

def eval_strategy(strategy):
    runner = BacktestRunner(store)
    result = runner.run(symbol, timeframe, strategy, start=start, end=end)
    equity = _extract_equity_curve(result["reports"]["account"])
    trades = _extract_trades(result["reports"]["positions"])
    m = calc_metrics(equity, trades) if not equity.empty else {}
    runner.dispose()
    return m

# === 1. EMA 网格：fast in [10,20,30], slow in [50,100,200] ===
print("=" * 82)
print("EMA 网格 | fast x slow | 100 USDT | 每笔 5 USDT | 23074 根")
print(f"{'配置':<18} {'最终权益':>10} {'收益率':>8} {'夏普':>6} {'回撤':>7} {'交易':>5} {'胜率':>6} {'盈亏比':>6}")
print("-" * 82)
ema_results = []
for fast, slow in itertools.product([10, 20, 30], [50, 100, 200]):
    if fast >= slow:
        continue
    strat = EMAShort(EMAShortConfig(instrument_id=instrument.id, bar_type=bar_type, trade_size=Decimal("5"), fast_ema_period=fast, slow_ema_period=slow))
    m = eval_strategy(strat)
    pf = m.get("profit_factor", 0)
    pf_s = f"{pf:.2f}" if pf != float("inf") and pf != 0 else ("inf" if pf == float("inf") else "0.00")
    label = f"EMA({fast},{slow})"
    tr = m.get('total_trades', 0) or 0
    print(f"{label:<18} ${m.get('final_equity',0):>8.2f} {m.get('total_return_pct',0):>7.2f}% {m.get('sharpe_ratio',0):>5.2f} -{m.get('max_drawdown_pct',0):>5.1f}% {tr:>4d} {m.get('win_rate_pct',0):>5.1f}% {pf_s:>6}")
    ema_results.append((label, m))

print()
# === 2. RSI 网格：oversold in [20,30,40], overbought in [60,70,80] ===
print("=" * 82)
print("RSI 网格 | oversold x overbought | RSI(14)")
print(f"{'配置':<18} {'最终权益':>10} {'收益率':>8} {'夏普':>6} {'回撤':>7} {'交易':>5} {'胜率':>6} {'盈亏比':>6}")
print("-" * 82)
rsi_results = []
for lo, hi in itertools.product([20, 30, 40], [60, 70, 80]):
    if lo >= hi:
        continue
    strat = RSIStrategy(RSIConfig(instrument_id=instrument.id, bar_type=bar_type, trade_size=Decimal("5"), rsi_period=14, oversold=float(lo), overbought=float(hi)))
    m = eval_strategy(strat)
    pf = m.get("profit_factor", 0)
    pf_s = f"{pf:.2f}" if pf != float("inf") and pf != 0 else ("inf" if pf == float("inf") else "0.00")
    label = f"RSI({lo},{hi})"
    tr = m.get('total_trades', 0) or 0
    print(f"{label:<18} ${m.get('final_equity',0):>8.2f} {m.get('total_return_pct',0):>7.2f}% {m.get('sharpe_ratio',0):>5.2f} -{m.get('max_drawdown_pct',0):>5.1f}% {tr:>4d} {m.get('win_rate_pct',0):>5.1f}% {pf_s:>6}")
    rsi_results.append((label, m))

print()
# === 总结：按收益率排序 ===
all_results = ema_results + rsi_results
all_results.sort(key=lambda x: x[1].get("final_equity", 0), reverse=True)
print("=" * 82)
print("Top 5 按最终权益排序")
print("-" * 82)
for label, m in all_results[:5]:
    print(f"  {label:<18} ${m.get('final_equity',0):.2f}  {m.get('total_return_pct',0):+.2f}%  夏普{m.get('sharpe_ratio',0):.2f}  回撤-{m.get('max_drawdown_pct',0):.1f}%  {m.get('total_trades',0)}笔  胜率{m.get('win_rate_pct',0):.1f}%")
print("=" * 82)

store.close()
