"""
Bollinger Bands indicator.
Generates variants for each (window, num_std) in config.BOLLINGER_PARAMS.
"""

import logging

import pandas as pd

from indicators import register
from indicators.base import BaseIndicator
import config

logger = logging.getLogger(__name__)


@register
class BollingerIndicator(BaseIndicator):

    def __init__(self, window: int = 20, num_std: float = 2.0):
        self.window = window
        self.num_std = num_std

    @property
    def name(self) -> str:
        std_str = str(self.num_std).replace(".", "p")
        return f"bb_{self.window}_{std_str}"

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        prefix = self.name
        logger.debug(f"Computing Bollinger Bands (window={self.window}, std={self.num_std}) on {len(df)} rows")
        mid = df["close"].rolling(window=self.window).mean()
        std = df["close"].rolling(window=self.window).std()
        df[f"{prefix}_mid"] = mid
        df[f"{prefix}_upper"] = mid + (std * self.num_std)
        df[f"{prefix}_lower"] = mid - (std * self.num_std)
        logger.debug(f"Bollinger tail:\n{df[[f'{prefix}_mid', f'{prefix}_upper', f'{prefix}_lower']].tail()}")
        return df

    @classmethod
    def get_variants(cls):
        return [cls(window=w, num_std=s) for w, s in config.BOLLINGER_PARAMS]
