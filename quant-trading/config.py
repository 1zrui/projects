"""
量化交易系统配置
"""

# ========== 交易所配置 ==========
EXCHANGE = "binance"
API_KEY = ""  # 实盘时填写
API_SECRET = ""  # 实盘时填写

# ========== 数据配置 ==========
# 默认交易对
SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
]

# 默认时间周期
TIMEFRAME = "4h"  # 1m, 5m, 15m, 1h, 4h, 1d (4h优化后效果最好)

# 回测数据起止时间
BACKTEST_START = "2024-01-01"
BACKTEST_END = "2025-12-31"

# ========== 回测配置 ==========
INITIAL_CAPITAL = 100  # 初始资金 (USDT)
COMMISSION = 0.001  # 手续费率 (0.1%)
SLIPPAGE = 0.0005  # 滑点 (0.05%)

# ========== 风控配置 ==========
MAX_POSITION_PCT = 0.3  # 单笔最大仓位占比
STOP_LOSS_PCT = 0.01  # 止损比例 (1%) - 优化后
TAKE_PROFIT_PCT = 0.08  # 止盈比例 (8%) - 优化后
