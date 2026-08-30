"""绩效指标计算

指标：
  - 总收益率 / 年化收益率
  - 夏普比率
  - 最大回撤
  - 胜率 / 盈亏比
  - 交易次数
  - 收益曲线
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def calc_metrics(equity_curve: pd.Series, trades: pd.DataFrame | None = None) -> dict:
    """计算核心绩效指标

    Args:
        equity_curve: 资金曲线（时间序列，index=时间，value=权益）
        trades: 交易记录（可选，包含 pnl 列）

    Returns:
        { 指标名: 值 }
    """
    metrics: dict = {}

    if equity_curve.empty:
        return {"error": "空资金曲线"}

    initial = equity_curve.iloc[0]
    final = equity_curve.iloc[-1]
    total_return = (final - initial) / initial

    metrics["initial_capital"] = float(initial)
    metrics["final_equity"] = float(final)
    metrics["total_return_pct"] = round(float(total_return) * 100, 2)
    metrics["pnl"] = float(final - initial)

    # 年化收益率
    days = (equity_curve.index[-1] - equity_curve.index[0]).days
    if days > 0:
        ann_return = (1 + total_return) ** (365 / days) - 1
        metrics["annual_return_pct"] = round(float(ann_return) * 100, 2)
    else:
        metrics["annual_return_pct"] = 0.0

    # 最大回撤
    peak = equity_curve.expanding().max()
    drawdown = (equity_curve - peak) / peak
    max_dd = drawdown.min()
    metrics["max_drawdown_pct"] = round(float(abs(max_dd)) * 100, 2)

    # 夏普比率（假设无风险利率=0，使用日收益率）
    daily_returns = equity_curve.pct_change().dropna()
    if len(daily_returns) > 1 and daily_returns.std() > 0:
        sharpe = np.sqrt(365) * daily_returns.mean() / daily_returns.std()
        metrics["sharpe_ratio"] = round(float(sharpe), 2)
    else:
        metrics["sharpe_ratio"] = 0.0

    # 交易统计
    if trades is not None and not trades.empty:
        # 假设 trades 有 pnl 列
        if "pnl" in trades.columns:
            winning = trades[trades["pnl"] > 0]
            losing = trades[trades["pnl"] < 0]
            metrics["total_trades"] = len(trades)
            metrics["winning_trades"] = len(winning)
            metrics["losing_trades"] = len(losing)
            metrics["win_rate_pct"] = round(len(winning) / len(trades) * 100, 2) if len(trades) > 0 else 0.0
            metrics["avg_win"] = float(winning["pnl"].mean()) if len(winning) > 0 else 0.0
            metrics["avg_loss"] = float(losing["pnl"].mean()) if len(losing) > 0 else 0.0
            metrics["profit_factor"] = round(
                float(winning["pnl"].sum() / abs(losing["pnl"].sum())), 2
            ) if len(losing) > 0 and losing["pnl"].sum() != 0 else float("inf")
        metrics["gross_profit"] = float(trades[trades["pnl"] > 0]["pnl"].sum()) if "pnl" in trades.columns else 0.0
        metrics["gross_loss"] = float(abs(trades[trades["pnl"] < 0]["pnl"].sum())) if "pnl" in trades.columns else 0.0

    return metrics


def calc_drawdown_series(equity_curve: pd.Series) -> pd.Series:
    """计算回撤序列"""
    peak = equity_curve.expanding().max()
    return (equity_curve - peak) / peak * 100  # 百分比


def calc_equity_curve_from_trades(
    initial_capital: float,
    trades: pd.DataFrame,
    price_series: pd.Series | None = None,
) -> pd.Series:
    """从交易记录重建资金曲线

    Args:
        initial_capital: 初始资金
        trades: 交易记录，必须含 exit_time, pnl 列
        price_series: 价格序列（用于未平仓市值）
    Returns:
        资金曲线 Series
    """
    if "exit_time" not in trades.columns or "pnl" not in trades.columns:
        raise ValueError("trades 需要 exit_time 和 pnl 列")

    # 按时间累计收益
    cum_pnl = trades.set_index("exit_time")["pnl"].sort_index().cumsum()
    equity = cum_pnl + initial_capital
    equity.name = "equity"
    return equity