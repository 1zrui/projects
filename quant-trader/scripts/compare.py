"""策略对比 —— 跑完输出三策略横向对比表"""

from decimal import Decimal

import yaml

from analysis.metrics import calc_metrics
from analysis.report import _extract_equity_curve, _extract_trades
from backtest.adapter import create_crypto_instrument, kline_to_bar_type
from data.store import MarketStore
from pathlib import Path
from strategies.examples.bollinger_mean_reversion import (
    BollingerMeanReversion,
    BollingerMeanReversionConfig,
)
from strategies.examples.ema_cross import EMACross, EMACrossConfig
from strategies.examples.rsi_strategy import RSIConfig, RSIStrategy

from backtest.runner import BacktestRunner

cfg = yaml.safe_load(open("config.yaml"))
store = MarketStore(Path(cfg["store"]["path"]))

symbol = "BTC/USDT"
timeframe = "1h"
instrument = create_crypto_instrument(symbol)
bar_type = kline_to_bar_type(symbol, "BINANCE", timeframe)

bt_cfg = cfg.get("backtest", {})
start = bt_cfg.get("start", "2024-01-01")
end = bt_cfg.get("end")  # null -> 最新数据

strategies = [
    ("EMA交叉", EMACross(EMACrossConfig(instrument_id=instrument.id, bar_type=bar_type, trade_size=Decimal("5")))),
    ("布林带", BollingerMeanReversion(BollingerMeanReversionConfig(instrument_id=instrument.id, bar_type=bar_type, trade_size=Decimal("5")))),
    ("RSI", RSIStrategy(RSIConfig(instrument_id=instrument.id, bar_type=bar_type, trade_size=Decimal("5")))),
]

# 先取一次区间信息做标题
from data.store import MarketStore as _MS  # noqa

print("=" * 78)
print(f"策略对比 | {symbol} {timeframe} | 100 USDT 本金 | 每笔 5 USDT | {start} ~ {end or '最新'}")
print("=" * 78)
print(f"{'策略':<10} {'最终权益':>10} {'收益率':>8} {'夏普':>6} {'回撤':>7} {'交易':>5} {'胜率':>6} {'盈亏比':>6}")
print("-" * 78)

runner = BacktestRunner(store)
for name, strategy in strategies:
    result = runner.run(symbol, timeframe, strategy, start=start, end=end)
    reports = result["reports"]
    equity = _extract_equity_curve(reports.get("account"))
    trades = _extract_trades(reports.get("positions"))
    if equity.empty:
        print(f"{name:<10} 无账户数据")
    else:
        m = calc_metrics(equity, trades)
        pf = m.get("profit_factor", 0)
        pf_str = f"{pf:.2f}" if pf != float("inf") else "inf"
        print(
            f"{name:<10} ${m.get('final_equity', 0):>8.2f} {m.get('total_return_pct', 0):>7.2f}% "
            f"{m.get('sharpe_ratio', 0):>5.2f} -{m.get('max_drawdown_pct', 0):>5.1f}% "
            f"{m.get('total_trades', 0):>4d} {m.get('win_rate_pct', 0):>5.1f}% {pf_str:>6}"
        )
    runner.dispose()

store.close()
print("=" * 78)
print("✅ 对比完成")
