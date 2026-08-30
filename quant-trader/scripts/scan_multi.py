"""横扫：EMA vs Donchian vs 买入持有基准，多币种对比"""
from decimal import Decimal
from pathlib import Path
import yaml
from analysis.report import _extract_equity_curve, _extract_trades
from analysis.metrics import calc_metrics
from backtest.adapter import create_crypto_instrument, kline_to_bar_type
from backtest.runner import BacktestRunner
from data.store import MarketStore
from strategies.examples.ema_short import EMAShort, EMAShortConfig
from strategies.examples.donchian_breakout import DonchianBreakout, DonchianBreakoutConfig

cfg = yaml.safe_load(open("config.yaml"))
store = MarketStore(Path(cfg["store"]["path"]))
bt_cfg = cfg.get("backtest", {})
start = bt_cfg.get("start", "2024-01-01")
end = bt_cfg.get("end")

# 计算买入持有的基准（直接用K线首尾价算）
def buy_hold_return(symbol, start, end):
    import duckdb
    db_path = cfg["store"]["path"]
    con = duckdb.connect(str(Path(db_path)))
    # 查首尾收盘价
    row = con.execute(
        "SELECT first(close ORDER BY timestamp), last(close ORDER BY timestamp) FROM klines WHERE symbol=? AND timeframe='1h' AND timestamp >= ? ORDER BY timestamp",
        [symbol, start]
    ).fetchone()
    if row and row[0]:
        return (row[1] - row[0]) / row[0] * 100
    return 0

symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "DOGE/USDT"]
timeframe = "1h"

# 先打印买入持有基准
print("买入持有基准 (2024-01-01 ~ 最新 1h):")
for sym in symbols:
    # 用store直接查
    df = store.query_kline(sym, "1h", start=start, end=end)
    if not df.empty:
        bh = (df["close"].iloc[-1] - df["close"].iloc[0]) / df["close"].iloc[0] * 100
        print(f"  {sym:<12} {bh:+7.2f}%  ({df['close'].iloc[0]:.2f} -> {df['close'].iloc[-1]:.2f})")

print()
print("=" * 108)
print(f"{'策略':<30} {'最终权益':>10} {'收益率':>8} {'夏普':>6} {'回撤':>7} {'交易':>5} {'胜率':>6} {'盈亏比':>6}")
print("-" * 108)

def eval_one(label, strategy, symbol, tf):
    instrument = create_crypto_instrument(symbol)
    bar_type = kline_to_bar_type(symbol, "BINANCE", tf)
    # strategy的instrument/bar_type在外部已设好
    runner = BacktestRunner(store)
    result = runner.run(symbol, tf, strategy, start=start, end=end)
    equity = _extract_equity_curve(result["reports"]["account"])
    trades = _extract_trades(result["reports"]["positions"])
    m = calc_metrics(equity, trades) if not equity.empty else {}
    pf = m.get("profit_factor", 0)
    pf_s = f"{pf:.2f}" if pf not in (0, None) and pf != float("inf") else ("inf" if pf == float("inf") else "0.00")
    print(f"{label:<30} ${m.get('final_equity',0):>8.2f} {m.get('total_return_pct',0):>7.2f}% {m.get('sharpe_ratio',0):>5.2f} -{m.get('max_drawdown_pct',0):>5.1f}% {m.get('total_trades',0) or 0:>4d} {m.get('win_rate_pct',0):>5.1f}% {pf_s:>6}")
    runner.dispose()
    return m

for sym in symbols:
    print(f"\n--- {sym} ---")
    inst = create_crypto_instrument(sym)
    bt = kline_to_bar_type(sym, "BINANCE", timeframe)

    # EMA 20/200
    eval_one(f"  EMA(20,200)", EMAShort(EMAShortConfig(instrument_id=inst.id, bar_type=bt, trade_size=Decimal("5"), fast_ema_period=20, slow_ema_period=200)), sym, timeframe)
    # EMA 20/50
    eval_one(f"  EMA(20,50)", EMAShort(EMAShortConfig(instrument_id=inst.id, bar_type=bt, trade_size=Decimal("5"), fast_ema_period=20, slow_ema_period=50)), sym, timeframe)
    # Donchian 20/10 + 3%止损6%止盈
    eval_one(f"  Donchian(20,10) SL3%TP6%", DonchianBreakout(DonchianBreakoutConfig(instrument_id=inst.id, bar_type=bt, trade_size=Decimal("5"), entry_period=20, exit_period=10, stop_loss_pct=0.03, take_profit_pct=0.06)), sym, timeframe)
    # Donchian 20/10 无止损止盈（纯通道）
    eval_one(f"  Donchian(20,10) 纯通道", DonchianBreakout(DonchianBreakoutConfig(instrument_id=inst.id, bar_type=bt, trade_size=Decimal("5"), entry_period=20, exit_period=10, stop_loss_pct=1.0, take_profit_pct=10.0)), sym, timeframe)

store.close()
print("=" * 108)
