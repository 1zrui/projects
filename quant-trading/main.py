"""
量化交易系统 - 主入口

用法:
    python main.py                          # 默认回测
    python main.py --symbol BTC/USDT        # 指定交易对
    python main.py --fetch                  # 先拉数据再回测
    python main.py --optimize               # 参数优化
    python main.py --compare                # 对比策略
    python main.py --fixed-size 0.3         # 固定30%仓位
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import SYMBOLS, TIMEFRAME, INITIAL_CAPITAL
from data_fetcher import fetch_ohlcv, save_data, load_data
from strategies import compute_indicators, generate_signals, strategy_simple_ma
from backtest_engine import (
    run_backtest, run_backtest_fixed_size, 
    get_metrics, compare_strategies, optimize_params
)


def main():
    parser = argparse.ArgumentParser(description="加密货币量化回测系统")
    parser.add_argument("--symbol", default="BTC/USDT", help="交易对")
    parser.add_argument("--timeframe", default=TIMEFRAME, help="K线周期")
    parser.add_argument("--fetch", action="store_true", help="拉取数据")
    parser.add_argument("--compare", action="store_true", help="对比策略")
    parser.add_argument("--optimize", action="store_true", help="参数优化")
    parser.add_argument("--fixed-size", type=float, default=None, help="固定仓位比例 (0-1)")
    parser.add_argument("--stop-loss", type=float, default=None, help="止损比例")
    parser.add_argument("--take-profit", type=float, default=None, help="止盈比例")
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"  量化回测系统 | {args.symbol} | {args.timeframe} | 本金 {INITIAL_CAPITAL} USDT")
    print("=" * 60)
    
    # ========== 1. 获取数据 ==========
    print("\n[1/4] 获取数据...")
    
    if args.fetch:
        df = fetch_ohlcv(args.symbol, args.timeframe)
        save_data(df, args.symbol, args.timeframe)
    else:
        try:
            df = load_data(args.symbol, args.timeframe)
        except FileNotFoundError:
            print("本地无数据，自动拉取...")
            df = fetch_ohlcv(args.symbol, args.timeframe)
            save_data(df, args.symbol, args.timeframe)
    
    # ========== 2. 计算指标 ==========
    print("\n[2/4] 计算技术指标...")
    df = compute_indicators(df)
    
    # ========== 3. 参数优化 ==========
    if args.optimize:
        print("\n[3/4] 参数优化中（网格搜索）...")
        result_df = optimize_params(df)
        
        print("\n" + "=" * 60)
        print("  参数优化结果 (Top 10)")
        print("=" * 60)
        print(result_df.head(10).to_string(index=False))
        
        # 用最佳参数回测
        best = result_df.iloc[0]
        print(f"\n最佳参数: RSI买入={best['RSI_买入']}, RSI卖出={best['RSI_卖出']}, "
              f"止损={best['止损']}, 止盈={best['止盈']}")
        
        return
    
    # ========== 3. 生成信号 ==========
    print("\n[3/4] 生成交易信号...")
    df_signals = generate_signals(df)
    
    buys = df_signals[df_signals["signal"] == 1]
    sells = df_signals[df_signals["signal"] == -1]
    print(f"  买入信号: {len(buys)} 次")
    print(f"  卖出信号: {len(sells)} 次")
    
    # ========== 4. 回测 ==========
    print("\n[4/4] 运行回测...")
    
    if args.compare:
        df_ma = strategy_simple_ma(df)
        strategies = {
            "多因子动量": df_signals,
            "双均线交叉": df_ma,
        }
        result = compare_strategies(df, strategies)
        print("\n" + "=" * 60)
        print("  策略对比结果")
        print("=" * 60)
        print(result.to_string())
    else:
        # 选择回测模式
        if args.fixed_size:
            portfolio = run_backtest_fixed_size(
                df_signals, 
                size_pct=args.fixed_size,
                stop_loss=args.stop_loss,
                take_profit=args.take_profit
            )
            mode = f"固定仓位 {args.fixed_size*100:.0f}%"
        else:
            portfolio = run_backtest(
                df_signals,
                stop_loss=args.stop_loss,
                take_profit=args.take_profit
            )
            mode = "全仓进出"
        
        metrics = get_metrics(portfolio)
        
        print("\n" + "=" * 60)
        print(f"  回测结果 - 多因子动量策略 ({mode})")
        print("=" * 60)
        for k, v in metrics.items():
            print(f"  {k}: {v}")
        
        # 输出最近交易
        print("\n最近5笔交易:")
        trades = portfolio.trades.records_readable
        if len(trades) > 0:
            cols = ["Entry Timestamp", "Avg Entry Price", "Exit Timestamp", "Avg Exit Price", "Return", "PnL"]
            print(trades[cols].tail())
    
    print("\n完成!")


if __name__ == "__main__":
    main()
