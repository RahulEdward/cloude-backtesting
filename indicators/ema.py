"""
EMA (Exponential Moving Average) crossover indicator.
Generates variants for each (fast, slow) pair in config.EMA_PERIODS.
"""

import logging

import pandas as pd

from indicators import register
from indicators.base import BaseIndicator
import config

logger = logging.getLogger(__name__)


@register
class EMAIndicator(BaseIndicator):

    def __init__(self, fast_period: int = 9, slow_period: int = 21):
        self.fast_period = fast_period
        self.slow_period = slow_period

    @property
    def name(self) -> str:
        return f"ema_{self.fast_period}_{self.slow_period}"

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        fast_col = f"ema_fast_{self.fast_period}_{self.slow_period}"
        slow_col = f"ema_slow_{self.fast_period}_{self.slow_period}"
        logger.debug(f"Computing EMA cross (fast={self.fast_period}, slow={self.slow_period}) on {len(df)} rows")
        df[fast_col] = df["close"].ewm(span=self.fast_period, adjust=False).mean()
        df[slow_col] = df["close"].ewm(span=self.slow_period, adjust=False).mean()
        logger.debug(f"EMA fast tail:\n{df[fast_col].tail()}")
        return df

    @classmethod
    def get_variants(cls):
        return [cls(fast_period=f, slow_period=s) for f, s in config.EMA_PERIODS]
