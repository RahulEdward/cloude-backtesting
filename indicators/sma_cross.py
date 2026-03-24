"""
SMA (Simple Moving Average) crossover indicator.
Generates variants for each (fast, slow) pair in config.SMA_PERIODS.
"""

import logging

import pandas as pd

from indicators import register
from indicators.base import BaseIndicator
import config

logger = logging.getLogger(__name__)


@register
class SMACrossIndicator(BaseIndicator):

    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        self.fast_period = fast_period
        self.slow_period = slow_period

    @property
    def name(self) -> str:
        return f"sma_{self.fast_period}_{self.slow_period}"

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        fast_col = f"sma_fast_{self.fast_period}_{self.slow_period}"
        slow_col = f"sma_slow_{self.fast_period}_{self.slow_period}"
        logger.debug(f"Computing SMA cross (fast={self.fast_period}, slow={self.slow_period}) on {len(df)} rows")
        df[fast_col] = df["close"].rolling(window=self.fast_period).mean()
        df[slow_col] = df["close"].rolling(window=self.slow_period).mean()
        logger.debug(f"SMA fast tail:\n{df[fast_col].tail()}")
        return df

    @classmethod
    def get_variants(cls):
        return [cls(fast_period=f, slow_period=s) for f, s in config.SMA_PERIODS]
