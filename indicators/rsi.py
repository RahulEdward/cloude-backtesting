"""
RSI (Relative Strength Index) indicator.
Generates variants for each period in config.RSI_PERIODS.
"""

import logging

import pandas as pd
import ta

from indicators import register
from indicators.base import BaseIndicator
import config

logger = logging.getLogger(__name__)


@register
class RSIIndicator(BaseIndicator):

    def __init__(self, period: int = 14):
        self.period = period

    @property
    def name(self) -> str:
        return f"rsi_{self.period}"

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        col = f"rsi_{self.period}"
        logger.debug(f"Computing RSI(period={self.period}) on {len(df)} rows")
        df[col] = ta.momentum.rsi(df["close"], window=self.period)
        logger.debug(f"RSI({self.period}) tail:\n{df[col].tail()}")
        return df

    @classmethod
    def get_variants(cls):
        return [cls(period=p) for p in config.RSI_PERIODS]
