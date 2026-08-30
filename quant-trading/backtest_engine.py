"""
回测引擎 - 基于 vectorbt (优化版)
"""

import vectorbt as vbt
import pandas as pd
import numpy as np
from config import INITIAL_CAPITAL, COMMISSION, SLIPPAGE, STOP_LOSS_PCT, TAKE_PROFIT_PCT, MAX_POSITION_PCT


def run_backtest(df: pd.DataFrame, 
                 stop_loss: float = None,
                 take_profit: float = None,
                 init_cash: float = None) -> vbt.Portfolio:
    """
    运行回测（带止损止盈）
    
    Args:
        df: 包含 signal 列的 DataFrame (1=买入, -1=卖出, 0=持有)
        stop_loss: 止损比例，None用config默认值
        take_profit: 止盈比例，None用config默认值
        init_cash: 初始资金，None用config默认值
    
    Returns:
        vectorbt Portfolio 对象
    """
    entries = df["signal"] == 1
    exits = df["signal"] == -1
    
    sl = stop_loss or STOP_LOSS_PCT
    tp = take_profit or TAKE_PROFIT_PCT
    cash = init_cash or INITIAL_CAPITAL
    
    portfolio = vbt.Portfolio.from_signals(
        close=df["close"],
        entries=entries,
        exits=exits,
        init_cash=cash,
        fees=COMMISSION,
        slippage=SLIPPAGE,
        sl_stop=sl,  # 止损
        tp_stop=tp,  # 止盈
        freq="1h",
    )
    
    return portfolio


def run_backtest_fixed_size(df: pd.DataFrame,
                             size_pct: float = None,
                             stop_loss: float = None,
                             take_profit: float = None,
                             init_cash: float = None) -> vbt.Portfolio:
    """
    固定仓位比例回测
    
    Args:
        size_pct: 每次开仓占总资金的比例 (0-1)
    """
    entries = df["signal"] == 1
    exits = df["signal"] == -1
    
    sl = stop_loss or STOP_LOSS_PCT
    tp = take_profit or TAKE_PROFIT_PCT
    cash = init_cash or INITIAL_CAPITAL
    pct = size_pct or MAX_POSITION_PCT
    
    # 计算固定仓位大小（基于初始资金）
    size = cash * pct
    
    portfolio = vbt.Portfolio.from_signals(
        close=df["close"],
        entries=entries,
        exits=exits,
        init_cash=cash,
        fees=COMMISSION,
        slippage=SLIPPAGE,
        sl_stop=sl,
        tp_stop=tp,
        size=size,  # 固定仓位大小
        freq="1h",
    )
    
    return portfolio


def optimize_params(df: pd.DataFrame,
                    rsi_buy_range: list = None,
                    rsi_sell_range: list = None,
                    stop_loss_range: list = None,
                    take_profit_range: list = None) -> pd.DataFrame:
    """
    参数优化 - 网格搜索最佳参数组合
    
    Returns:
        按收益排序的参数组合 DataFrame
    """
    from strategies import compute_indicators, generate_signals
    
    rsi_buys = rsi_buy_range or [25, 30, 35, 40]
    rsi_sells = rsi_sell_range or [60, 65, 70, 75]
    stop_losses = stop_loss_range or [0.01, 0.02, 0.03, 0.05]
    take_profits = take_profit_range or [0.03, 0.05, 0.08, 0.10]
    
    results = []
    
    total = len(rsi_buys) * len(rsi_sells) * len(stop_losses) * len(take_profits)
    count = 0
    
    for rsi_buy in rsi_buys:
        for rsi_sell in rsi_sells:
            for sl in stop_losses:
                for tp in take_profits:
                    count += 1
                    
                    try:
                        # 生成信号
                        temp_df = compute_indicators(df.copy())
                        temp_df = generate_signals(temp_df, rsi_buy=rsi_buy, rsi_sell=rsi_sell)
                        
                        # 回测
                        portfolio = run_backtest(temp_df, stop_loss=sl, take_profit=tp)
                        stats = portfolio.stats()
                        
                        results.append({
                            "RSI_买入": rsi_buy,
                            "RSI_卖出": rsi_sell,
                            "止损": f"{sl*100:.1f}%",
                            "止盈": f"{tp*100:.1f}%",
                            "总收益率": f"{stats['Total Return [%]']:.2f}%",
                            "最大回撤": f"{stats['Max Drawdown [%]']:.2f}%",
                            "夏普比率": f"{stats['Sharpe Ratio']:.2f}",
                            "胜率": f"{stats['Win Rate [%]']:.2f}%",
                            "交易次数": stats['Total Closed Trades'],
                            "收益数值": stats['Total Return [%]'],  # 用于排序
                        })
                        
                        if count % 10 == 0:
                            print(f"  优化进度: {count}/{total}")
                            
                    except Exception as e:
                        continue
    
    result_df = pd.DataFrame(results)
    result_df = result_df.sort_values("收益数值", ascending=False)
    result_df = result_df.drop(columns=["收益数值"])
    
    return result_df


def get_metrics(portfolio: vbt.Portfolio) -> dict:
    """获取回测指标"""
    stats = portfolio.stats()
    
    metrics = {
        "总收益率": f"{stats['Total Return [%]']:.2f}%",
        "最大回撤": f"{stats['Max Drawdown [%]']:.2f}%",
        "夏普比率": f"{stats['Sharpe Ratio']:.2f}",
        "Sortino比率": f"{stats['Sortino Ratio']:.2f}",
        "胜率": f"{stats['Win Rate [%]']:.2f}%",
        "盈亏比": f"{stats['Profit Factor']:.2f}",
        "交易次数": stats['Total Closed Trades'],
        "总手续费": f"{stats['Total Fees Paid']:.4f} USDT",
        "平均盈利": f"{stats['Avg Winning Trade [%]']:.2f}%",
        "平均亏损": f"{stats['Avg Losing Trade [%]']:.2f}%",
        "最终资金": f"{stats['End Value']:.2f} USDT",
    }
    
    return metrics


def compare_strategies(df: pd.DataFrame, strategies: dict) -> pd.DataFrame:
    """对比多个策略的回测结果"""
    results = {}
    
    for name, signal_df in strategies.items():
        try:
            portfolio = run_backtest(signal_df)
            metrics = get_metrics(portfolio)
            results[name] = metrics
        except Exception as e:
            results[name] = {"错误": str(e)}
    
    return pd.DataFrame(results).T
