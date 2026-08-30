"""
数据采集模块 - 从币安拉取K线数据
"""

import ccxt
import pandas as pd
import os
from datetime import datetime
from config import EXCHANGE, TIMEFRAME, BACKTEST_START, BACKTEST_END


def get_exchange():
    """获取交易所实例（国内需要走代理）"""
    exchange_class = getattr(ccxt, EXCHANGE)
    return exchange_class({
        "enableRateLimit": True,
        "options": {"defaultType": "spot"},
        "proxies": {
            "http": "http://127.0.0.1:20171",
            "https": "http://127.0.0.1:20171",
        },
    })


def fetch_ohlcv(symbol: str, timeframe: str = None, start: str = None, end: str = None) -> pd.DataFrame:
    """
    拉取K线数据
    
    Args:
        symbol: 交易对，如 "BTC/USDT"
        timeframe: K线周期，默认用config里的
        start: 开始日期 "YYYY-MM-DD"
        end: 结束日期 "YYYY-MM-DD"
    
    Returns:
        DataFrame with columns: [open, high, low, close, volume]
    """
    timeframe = timeframe or TIMEFRAME
    start = start or BACKTEST_START
    end = end or BACKTEST_END
    
    exchange = get_exchange()
    
    # 转换时间戳
    since = int(datetime.strptime(start, "%Y-%m-%d").timestamp() * 1000)
    end_ts = int(datetime.strptime(end, "%Y-%m-%d").timestamp() * 1000)
    
    all_data = []
    limit = 1000  # 币安单次最多1000条
    
    print(f"正在拉取 {symbol} {timeframe} 数据...")
    
    while since < end_ts:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            if not ohlcv:
                break
            
            all_data.extend(ohlcv)
            since = ohlcv[-1][0] + 1  # 下一条从最后一根K线之后开始
            
            print(f"  已拉取 {len(all_data)} 条")
        except Exception as e:
            print(f"  拉取出错: {e}，重试中...")
            continue
    
    if not all_data:
        raise ValueError(f"未获取到 {symbol} 的数据")
    
    # 转为DataFrame
    df = pd.DataFrame(all_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    
    # 去重
    df = df[~df.index.duplicated(keep="first")]
    
    # 过滤结束时间
    df = df[df.index <= end]
    
    print(f"完成: {symbol} 共 {len(df)} 条数据 [{df.index[0]} ~ {df.index[-1]}]")
    
    return df


def save_data(df: pd.DataFrame, symbol: str, timeframe: str = None):
    """保存数据到本地"""
    timeframe = timeframe or TIMEFRAME
    filename = symbol.replace("/", "_") + f"_{timeframe}.csv"
    filepath = os.path.join("data", filename)
    df.to_csv(filepath)
    print(f"已保存: {filepath}")
    return filepath


def load_data(symbol: str, timeframe: str = None) -> pd.DataFrame:
    """从本地加载数据"""
    timeframe = timeframe or TIMEFRAME
    filename = symbol.replace("/", "_") + f"_{timeframe}.csv"
    filepath = os.path.join("data", filename)
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"数据文件不存在: {filepath}，请先运行 fetch_ohlcv")
    
    df = pd.read_csv(filepath, index_col="timestamp", parse_dates=True)
    print(f"已加载: {filepath} ({len(df)} 条)")
    return df


if __name__ == "__main__":
    # 测试：拉取BTC/USDT数据并保存
    symbols = ["BTC/USDT", "ETH/USDT"]
    for sym in symbols:
        df = fetch_ohlcv(sym)
        save_data(df, sym)
        print()
