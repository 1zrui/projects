"""DOGE 深度寻优"""
from decimal import Decimal
from pathlib import Path
import itertools, yaml
from analysis.report import _extract_equity_curve, _extract_trades
from analysis.metrics import calc_metrics
from backtest.adapter import create_crypto_instrument, kline_to_bar_type
from backtest.runner import BacktestRunner
from data.store import MarketStore
from strategies.examples.ema_short import EMAShort, EMAShortConfig
from strategies.examples.donchian_breakout import DonchianBreakout, DonchianBreakoutConfig

cfg = yaml.safe_load(open("config.yaml"))
store = MarketStore(Path(cfg["store"]["path"]))
start, end = cfg["backtest"]["start"], cfg["backtest"]["end"]
symbol = "DOGE/USDT"
tf = "1h"
inst = create_crypto_instrument(symbol)
bt = kline_to_bar_type(symbol, "BINANCE", tf)

def eval_m(strat):
    r = BacktestRunner(store)
    res = r.run(symbol, tf, strat, start=start, end=end)
    eq = _extract_equity_curve(res["reports"]["account"])
    tr = _extract_trades(res["reports"]["positions"])
    m = calc_metrics(eq, tr) if not eq.empty else {}
    r.dispose()
    return m

print("=== DOGE EMA 网格 ===")
print(f"{'配置':<16} {'收益率':>8} {'夏普':>6} {'回撤':>7} {'交易':>5} {'胜率':>6} {'盈亏比':>6}")
best = None
for fast, slow in itertools.product([10,15,20,30,50], [50,100,150,200]):
    if fast >= slow: continue
    m = eval_m(EMAShort(EMAShortConfig(instrument_id=inst.id, bar_type=bt, trade_size=Decimal("5"), fast_ema_period=fast, slow_ema_period=slow)))
    pf = m.get("profit_factor",0)
    pfs = f"{pf:.2f}" if pf not in (0,None) and pf!=float("inf") else "inf"
    label=f"EMA({fast},{slow})"
    print(f"{label:<16} {m.get('total_return_pct',0):>7.2f}% {m.get('sharpe_ratio',0):>5.2f} -{m.get('max_drawdown_pct',0):>5.1f}% {m.get('total_trades',0) or 0:>4d} {m.get('win_rate_pct',0):>5.1f}% {pfs:>6}")
    if best is None or m.get("final_equity",0) > best[1].get("final_equity",0):
        best=(label,m)
print(f"\nEMA最优: {best[0]} -> {best[1].get('total_return_pct',0):.2f}%  权益${best[1].get('final_equity',0):.2f}")

print("\n=== DOGE Donchian 网格 (entry/exit) ===")
print(f"{'配置':<20} {'收益率':>8} {'夏普':>6} {'回撤':>7} {'交易':>5} {'胜率':>6} {'盈亏比':>6}")
best2=None
for ep, xp in itertools.product([10,20,30,50], [5,10,20]):
    if xp>=ep: continue
    m = eval_m(DonchianBreakout(DonchianBreakoutConfig(instrument_id=inst.id, bar_type=bt, trade_size=Decimal("5"), entry_period=ep, exit_period=xp, stop_loss_pct=1.0, take_profit_pct=10.0)))
    pf = m.get("profit_factor",0)
    pfs = f"{pf:.2f}" if pf not in (0,None) and pf!=float("inf") else "inf"
    label=f"Don({ep},{xp})"
    print(f"{label:<20} {m.get('total_return_pct',0):>7.2f}% {m.get('sharpe_ratio',0):>5.2f} -{m.get('max_drawdown_pct',0):>5.1f}% {m.get('total_trades',0) or 0:>4d} {m.get('win_rate_pct',0):>5.1f}% {pfs:>6}")
    if best2 is None or m.get("final_equity",0) > best2[1].get("final_equity",0):
        best2=(label,m)
print(f"\nDonchian最优: {best2[0]} -> {best2[1].get('total_return_pct',0):.2f}%  权益${best2[1].get('final_equity',0):.2f}")

print("\n=== DOGE EMA不同仓位(最优参数) ===")
fast,slow = 20,200
# 从best里解析
import re
mm=re.search(r"EMA\((\d+),(\d+)\)", best[0])
if mm:
    fast,slow=int(mm.group(1)),int(mm.group(2))
for sz in [5,10,20]:
    m = eval_m(EMAShort(EMAShortConfig(instrument_id=inst.id, bar_type=bt, trade_size=Decimal(str(sz)), fast_ema_period=fast, slow_ema_period=slow)))
    print(f"EMA({fast},{slow}) x{sz}U  -> {m.get('total_return_pct',0):+.2f}%  权益${m.get('final_equity',0):.2f}  回撤-{m.get('max_drawdown_pct',0):.1f}%  {m.get('total_trades',0)}笔  盈亏比{m.get('profit_factor',0):.2f}")

store.close()
