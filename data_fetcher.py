"""
Fetches OHLCV data from Binance public API and splits into train/test.
Caches to CSV so repeat runs load instantly.
No API key required - uses public kline endpoint.
"""

import logging
import os
import time
from datetime import datetime, timedelta

import pandas as pd
import requests

import config

logger = logging.getLogger(__name__)


def _cache_path(symbol: str, interval: str, lookback_days: int) -> str:
    """Build a unique CSV cache filename."""
    return os.path.join(
        config.CSV_CACHE_DIR,
        f"{symbol}_{interval}_{lookback_days}d.csv",
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
    df = fetch_binance_klines(config.SYMBOL, config.TIMEFRAME, config.LOOKBACK_DAYS)
    train_df, test_df = split_train_test(df)
    return train_df, test_df
