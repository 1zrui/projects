"""回测报告生成 —— HTML + Plotly 可视化

产出：
  - 资金曲线图
  - 回撤曲线图
  - 月度收益热力图
  - 交易分布图
  - 完整 HTML 报告
"""

from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analysis.metrics import calc_drawdown_series, calc_metrics

REPORT_DIR = Path("reports")


def generate_html_report(
    result: dict[str, Any],
    output_path: str | Path | None = None,
) -> str:
    """生成完整 HTML 回测报告

    Args:
        result: runner.run() 的返回值，含 reports 和 engine
        output_path: 输出路径，默认 reports/backtest_{time}.html

    Returns:
        HTML 文件路径
    """
    reports = result.get("reports", {})
    config = reports.get("config", {})
    account_df = reports.get("account")
    positions_df = reports.get("positions")
    fills_df = reports.get("fills")

    # 准备数据
    equity_curve = _extract_equity_curve(account_df)
    trades_df = _extract_trades(positions_df)

    # 计算指标
    metrics = calc_metrics(equity_curve, trades_df) if not equity_curve.empty else {}

    # 生成图表
    charts_html = _build_charts(equity_curve, trades_df, metrics)

    # 构建报告
    title = f"{config.get('symbol', 'N/A')} {config.get('timeframe', 'N/A')} 回测报告"
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #0d1117; color: #c9d1d9; padding: 20px; }}
.container {{ max-width: 1200px; margin: 0 auto; }}
.header {{ margin-bottom: 24px; }}
.header h1 {{ font-size: 1.6em; color: #f0f6fc; }}
.header .meta {{ color: #8b949e; font-size: 0.85em; margin-top: 4px; }}
.metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
                gap: 12px; margin-bottom: 24px; }}
.metric-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px;
               padding: 14px; }}
.metric-card .label {{ font-size: 0.75em; color: #8b949e; text-transform: uppercase; }}
.metric-card .value {{ font-size: 1.4em; font-weight: 600; margin-top: 4px; }}
.metric-card .value.positive {{ color: #3fb950; }}
.metric-card .value.negative {{ color: #f85149; }}
.chart {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px;
         padding: 16px; margin-bottom: 16px; }}
.chart h3 {{ font-size: 0.9em; color: #8b949e; margin-bottom: 8px; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid #30363d; font-size: 0.85em; }}
th {{ color: #8b949e; font-weight: 500; }}
td {{ color: #c9d1d9; }}
tr:hover {{ background: #1c2128; }}
.section-title {{ font-size: 1.1em; color: #f0f6fc; margin: 20px 0 12px; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
  <h1>{title}</h1>
  <div class="meta">
    回测区间: {config.get('start', 'N/A')} ~ {config.get('end', 'N/A')} &nbsp;|&nbsp;
    初始资金: ${config.get('initial_capital', 'N/A')} &nbsp;|&nbsp;
    数据量: {config.get('bars', 'N/A')} 根K线 &nbsp;|&nbsp;
    生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
  </div>
</div>

<div class="metrics-grid">
  <div class="metric-card">
    <div class="label">总收益率</div>
    <div class="value {'positive' if metrics.get('total_return_pct', 0) > 0 else 'negative'}">
      {metrics.get('total_return_pct', 'N/A')}%
    </div>
  </div>
  <div class="metric-card">
    <div class="label">年化收益率</div>
    <div class="value {'positive' if metrics.get('annual_return_pct', 0) > 0 else 'negative'}">
      {metrics.get('annual_return_pct', 'N/A')}%
    </div>
  </div>
  <div class="metric-card">
    <div class="label">夏普比率</div>
    <div class="value {'positive' if metrics.get('sharpe_ratio', 0) > 0 else 'negative'}">
      {metrics.get('sharpe_ratio', 'N/A')}
    </div>
  </div>
  <div class="metric-card">
    <div class="label">最大回撤</div>
    <div class="value negative">
      -{metrics.get('max_drawdown_pct', 'N/A')}%
    </div>
  </div>
  <div class="metric-card">
    <div class="label">总交易</div>
    <div class="value">{metrics.get('total_trades', 'N/A')}</div>
  </div>
  <div class="metric-card">
    <div class="label">胜率</div>
    <div class="value">{metrics.get('win_rate_pct', 'N/A')}%</div>
  </div>
  <div class="metric-card">
    <div class="label">盈亏比</div>
    <div class="value">{metrics.get('profit_factor', 'N/A')}</div>
  </div>
  <div class="metric-card">
    <div class="label">最终权益</div>
    <div class="value">${metrics.get('final_equity', 'N/A')}</div>
  </div>
</div>

{charts_html}

<div class="section-title">交易明细</div>
<div class="chart">
  {_build_table(trades_df, 'positions')}
</div>

<div class="section-title">成交记录</div>
<div class="chart">
  {_build_table(fills_df, 'fills')}
</div>

</div>
</body>
</html>"""

    # 写入文件
    output_path = output_path or REPORT_DIR / f"backtest_{datetime.now():%Y%m%d_%H%M%S}.html"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    print(f"[report] 报告已生成: {output_path.resolve()}")
    return str(output_path)


def _build_charts(
    equity_curve: pd.Series,
    trades_df: pd.DataFrame | None,
    metrics: dict,
) -> str:
    """构建图表 HTML"""
    if equity_curve.empty:
        return '<div class="chart"><p>无资金曲线数据</p></div>'

    charts = ""

    # 1. 资金曲线 + 回撤
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.05,
    )

    fig.add_trace(
        go.Scatter(x=equity_curve.index, y=equity_curve.values,
                   mode="lines", name="权益",
                   line=dict(color="#3fb950", width=2)),
        row=1, col=1,
    )

    drawdown = calc_drawdown_series(equity_curve)
    fig.add_trace(
        go.Scatter(x=drawdown.index, y=drawdown.values,
                   mode="lines", name="回撤",
                   line=dict(color="#f85149", width=1),
                   fill="tozeroy", fillcolor="rgba(248,81,73,0.15)"),
        row=2, col=1,
    )

    fig.update_layout(
        template="plotly_dark",
        height=500,
        margin=dict(l=40, r=20, t=20, b=40),
        showlegend=False,
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="权益 (USDT)", row=1, col=1)
    fig.update_yaxes(title_text="回撤 (%)", row=2, col=1, tickformat=".1f")
    charts += f'<div class="chart"><h3>📈 资金曲线 & 回撤</h3>{fig.to_html(include_plotlyjs=False, full_html=False)}</div>'

    # 2. 交易盈亏分布
    if trades_df is not None and not trades_df.empty and "pnl" in trades_df.columns:
        fig2 = go.Figure()
        colors = ["#3fb950" if v >= 0 else "#f85149" for v in trades_df["pnl"]]
        fig2.add_trace(
            go.Bar(x=trades_df.index, y=trades_df["pnl"],
                   marker_color=colors, name="盈亏"),
        )
        fig2.update_layout(
            template="plotly_dark",
            height=300,
            margin=dict(l=40, r=20, t=20, b=40),
            showlegend=False,
            hovermode="x unified",
            xaxis_title="交易序号",
            yaxis_title="盈亏 (USDT)",
        )
        charts += f'<div class="chart"><h3>📊 交易盈亏分布</h3>{fig2.to_html(include_plotlyjs=False, full_html=False)}</div>'

    return charts


def _build_table(df: pd.DataFrame | None | str, name: str) -> str:
    """构建 HTML 表格"""
    if df is None:
        return "<p>无数据</p>"
    if isinstance(df, str):
        return f"<p>{df}</p>"
    if df.empty:
        return "<p>无记录</p>"

    # 限制显示行数
    if len(df) > 100:
        df = df.head(100)

    # 格式化数值
    float_cols = df.select_dtypes(include=["float64"]).columns
    for col in float_cols:
        df[col] = df[col].round(4)

    thead = "".join(f"<th>{c}</th>" for c in df.columns)
    tbody = ""
    for _, row in df.iterrows():
        cells = "".join(f"<td>{v}</td>" for v in row)
        tbody += f"<tr>{cells}</tr>"

    return f"""<div style="max-height:400px;overflow-y:auto;">
<table><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>
<p style="color:#8b949e;font-size:0.8em;margin-top:8px;">
{'仅显示前 100 行' if len(df) == 100 else f'共 {len(df)} 行'}
</p></div>"""


def _extract_equity_curve(account_df: pd.DataFrame | None | str) -> pd.Series:
    """从账户报告提取资金曲线（USDT 权益）"""
    if account_df is None or isinstance(account_df, str):
        return pd.Series(dtype=float)
    if account_df.empty:
        return pd.Series(dtype=float)
    # nautilus: total 是 str，currency 分 USDT/BTC 两行，只取 USDT
    if "total" in account_df.columns and "currency" in account_df.columns:
        df = account_df[account_df["currency"] == "USDT"].copy()
        if df.empty:
            return pd.Series(dtype=float)
        # total 是 "100.00000000" 字符串，转 float
        equity = pd.to_numeric(df["total"], errors="coerce")
        equity.index = pd.to_datetime(df.index)
        equity = equity.sort_index().astype(float)
        equity.name = "equity"
        return equity
    # 兜底：旧字段名
    if "balance" in account_df.columns and "ts" in account_df.columns:
        equity = account_df.set_index("ts")["balance"]
        equity.index = pd.to_datetime(equity.index)
        return equity.astype(float)
    return pd.Series(dtype=float)


def _extract_trades(positions_df: pd.DataFrame | None | str) -> pd.DataFrame | None:
    """从持仓报告提取交易记录，转为 calc_metrics 期望的格式"""
    if positions_df is None or isinstance(positions_df, str):
        return None
    if positions_df.empty:
        return None
    # nautilus: realized_pnl 可能是 "1.23 USDT" 字符串或 Money 对象
    df = positions_df.copy()
    if "realized_pnl" in df.columns:
        # 先转 str 再按空格取首段，避免 Money 对象导致 extract 失效
        raw = df["realized_pnl"].astype(str)
        # "1.23 USDT" -> "1.23", "-0.15 USDT" -> "-0.15"
        df["pnl"] = pd.to_numeric(raw.str.split().str[0], errors="coerce")
    if "ts_closed" in df.columns:
        df["exit_time"] = pd.to_datetime(df["ts_closed"])
    return df