"""
Fetches OHLCV data from multiple sources and splits into train/test.
Supports: Crypto (Binance), Indian Stocks (Yahoo), Forex (Yahoo).
Caches to CSV so repeat runs load instantly.
"""

import logging
import os
import time
from datetime import datetime, timedelta

import pandas as pd
import requests

import config

logger = logging.getLogger(__name__)


# ─────────────────────── Cache Layer ───────────────────────


def _cache_path(symbol: str, interval: str, lookback_days: int) -> str:
    """Build a unique CSV cache filename."""
    safe_symbol = symbol.replace("=", "").replace("/", "").replace("^", "")
    return os.path.join(
        config.CSV_CACHE_DIR,
        f"{safe_symbol}_{interval}_{lookback_days}d.csv",
    )


def _load_cache(path: str) -> pd.DataFrame | None:
    """Load cached CSV if it exists and is fresh (less than 1 day old)."""
    if not os.path.exists(path):
        return None
    age_hours = (time.time() - os.path.getmtime(path)) / 3600
    if age_hours > 24:
        logger.info(f"Cache stale ({age_hours:.1f}h old), re-fetching")
        return None
    logger.info(f"Loading cached data from {path}")
    df = pd.read_csv(path, index_col="open_time", parse_dates=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    logger.info(f"Loaded {len(df)} cached candles")
    return df


def _save_cache(df: pd.DataFrame, path: str):
    """Save DataFrame to CSV cache."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path)
    logger.info(f"Saved {len(df)} candles to cache: {path}")


# ─────────────────────── Binance (Crypto) ───────────────────────


def fetch_binance_klines(symbol: str, interval: str, lookback_days: int) -> pd.DataFrame:
    """
    Fetch historical klines from Binance REST API.
    Uses CSV cache to avoid re-downloading. Paginates automatically.
    """
    cache_file = _cache_path(symbol, interval, lookback_days)
    cached = _load_cache(cache_file)
    if cached is not None:
        return cached

    logger.info(f"Fetching {symbol} {interval} data for last {lookback_days} days from Binance")

    base_url = "https://api.binance.com/api/v3/klines"
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=lookback_days)).timestamp() * 1000)

    all_klines = []
    current_start = start_time

    while current_start < end_time:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": current_start,
            "endTime": end_time,
            "limit": 1000,
        }

        logger.debug(f"Requesting klines from {datetime.fromtimestamp(current_start/1000)}")

        try:
            resp = requests.get(base_url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error(f"Binance API request failed: {e}")
            raise

        if not data:
            logger.debug("No more data returned, stopping pagination")
            break

        all_klines.extend(data)
        current_start = data[-1][0] + 1
        logger.debug(f"Fetched {len(data)} candles, total so far: {len(all_klines)}")

        time.sleep(0.2)

    if not all_klines:
        raise ValueError(f"No data returned from Binance for {symbol} {interval}")

    df = pd.DataFrame(all_klines, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df = df.set_index("open_time")
    df = df[["open", "high", "low", "close", "volume"]]
    df = df[~df.index.duplicated(keep="first")]
    df = df.sort_index()

    logger.info(f"Fetched {len(df)} candles from {df.index[0]} to {df.index[-1]}")
    logger.debug(f"Data shape: {df.shape}, dtypes:\n{df.dtypes}")

    _save_cache(df, cache_file)
    return df


# ─────────────────────── Yahoo Finance (Stocks + Forex) ───────────────────────


def fetch_yahoo_data(symbol: str, interval: str, lookback_days: int) -> pd.DataFrame:
    """
    Fetch historical data from Yahoo Finance via yfinance.
    Works for: Indian stocks (RELIANCE.NS), US stocks (AAPL), Forex (EURUSD=X), indices (^NSEI).
    """
    cache_file = _cache_path(symbol, interval, lookback_days)
    cached = _load_cache(cache_file)
    if cached is not None:
        return cached

    try:
        import yfinance as yf
    except ImportError:
        raise ImportError(
            "yfinance is required for stock/forex data. Install it:\n"
            "  pip install yfinance"
        )

    logger.info(f"Fetching {symbol} {interval} data for last {lookback_days} days from Yahoo Finance")

    # Yahoo Finance interval mapping
    yf_interval_map = {
        "1m": "1m", "5m": "5m", "15m": "15m",
        "1h": "1h", "4h": "1h",  # Yahoo doesn't support 4h, use 1h
        "1d": "1d", "1wk": "1wk", "1mo": "1mo",
    }
    yf_interval = yf_interval_map.get(interval, "1h")

    # Yahoo limits: 1m=7d, 5m/15m=60d, 1h=730d, 1d=unlimited
    if yf_interval in ["1m"] and lookback_days > 7:
        logger.warning(f"Yahoo limits 1m data to 7 days, clamping from {lookback_days}")
        lookback_days = 7
    elif yf_interval in ["5m", "15m"] and lookback_days > 60:
        logger.warning(f"Yahoo limits {yf_interval} data to 60 days, clamping from {lookback_days}")
        lookback_days = 60
    elif yf_interval == "1h" and lookback_days > 730:
        logger.warning(f"Yahoo limits 1h data to 730 days, clamping from {lookback_days}")
        lookback_days = 730

    ticker = yf.Ticker(symbol)
    df = ticker.history(period=f"{lookback_days}d", interval=yf_interval)

    if df.empty:
        raise ValueError(f"No data returned from Yahoo Finance for {symbol} {yf_interval}")

    # Normalize column names to lowercase
    df.columns = [c.lower() for c in df.columns]

    # Keep only OHLCV columns
    required = ["open", "high", "low", "close", "volume"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' missing from Yahoo data for {symbol}")

    df = df[required]
    df.index.name = "open_time"
    df = df[~df.index.duplicated(keep="first")]
    df = df.sort_index()

    # Remove timezone info if present (vectorbt works better without it)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    for col in required:
        df[col] = df[col].astype(float)

    # If user wanted 4h but Yahoo gave 1h, resample to 4h
    if interval == "4h" and yf_interval == "1h":
        logger.info("Resampling 1h data to 4h")
        df = df.resample("4h").agg({
            "open": "first", "high": "max", "low": "min",
            "close": "last", "volume": "sum",
        }).dropna()

    logger.info(f"Fetched {len(df)} candles from {df.index[0]} to {df.index[-1]}")
    logger.debug(f"Data shape: {df.shape}, dtypes:\n{df.dtypes}")

    _save_cache(df, cache_file)
    return df


# ─────────────────────── Unified Interface ───────────────────────


def fetch_data(symbol: str = None, interval: str = None, lookback_days: int = None,
               market: str = None) -> pd.DataFrame:
    """
    Fetch OHLCV data from the appropriate source based on MARKET config.
    Auto-detects: crypto → Binance, stock/forex → Yahoo Finance.
    """
    symbol = symbol or config.SYMBOL
    interval = interval or config.TIMEFRAME
    lookback_days = lookback_days or config.LOOKBACK_DAYS
    market = (market or config.MARKET).lower()

    if market == "crypto":
        return fetch_binance_klines(symbol, interval, lookback_days)
    elif market in ("stock", "forex"):
        return fetch_yahoo_data(symbol, interval, lookback_days)
    else:
        raise ValueError(
            f"Unknown MARKET '{market}'. Use 'crypto', 'stock', or 'forex'. "
            f"Set it in config.py"
        )


def split_train_test(df: pd.DataFrame, train_ratio: float = None):
    """Split dataframe into training (in-sample) and testing (out-of-sample) sets."""
    if train_ratio is None:
        train_ratio = config.TRAIN_RATIO

    split_idx = int(len(df) * train_ratio)
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()

    logger.info(
        f"Split data: train={len(train_df)} rows "
        f"({train_df.index[0]} to {train_df.index[-1]}), "
        f"test={len(test_df)} rows "
        f"({test_df.index[0]} to {test_df.index[-1]})"
    )

    return train_df, test_df


def get_data():
    """Convenience: fetch + split in one call."""
    df = fetch_data()
    train_df, test_df = split_train_test(df)
    return train_df, test_df
