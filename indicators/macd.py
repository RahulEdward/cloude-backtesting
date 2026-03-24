"""
MACD (Moving Average Convergence Divergence) indicator.
Generates variants for each (fast, slow, signal) in config.MACD_PARAMS.
"""

import logging

import pandas as pd
import ta

from indicators import register
from indicators.base import BaseIndicator
import config

logger = logging.getLogger(__name__)


@register
class MACDIndicator(BaseIndicator):

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    @property
    def name(self) -> str:
        return f"macd_{self.fast}_{self.slow}_{self.signal}"

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.debug(f"Computing MACD({self.fast},{self.slow},{self.signal}) on {len(df)} rows")
        macd_obj = ta.trend.MACD(
            df["close"],
            window_fast=self.fast,
            window_slow=self.slow,
            window_sign=self.signal,
        )
        prefix = f"macd_{self.fast}_{self.slow}_{self.signal}"
        df[f"{prefix}_line"] = macd_obj.macd()
        df[f"{prefix}_signal"] = macd_obj.macd_signal()
        df[f"{prefix}_hist"] = macd_obj.macd_diff()
        logger.debug(f"MACD tail:\n{df[[f'{prefix}_line', f'{prefix}_signal']].tail()}")
        return df

    @classmethod
    def get_variants(cls):
        return [cls(fast=f, slow=s, signal=sig) for f, s, sig in config.MACD_PARAMS]
