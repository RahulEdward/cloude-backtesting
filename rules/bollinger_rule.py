"""
Bollinger Bands rule.
Buy when price touches lower band, sell when price touches upper band.
Generates variants for each Bollinger parameter set.
"""

import logging

import pandas as pd

from rules import register
from rules.base import BaseRule
import config

logger = logging.getLogger(__name__)


@register
class BollingerRule(BaseRule):

    def __init__(self, window: int = 20, num_std: float = 2.0):
        self.window = window
        self.num_std = num_std

    @property
    def name(self) -> str:
        std_str = str(self.num_std).replace(".", "p")
        return f"BB({self.window},{self.num_std})"

    @property
    def required_indicators(self) -> list[str]:
        std_str = str(self.num_std).replace(".", "p")
        return [f"bb_{self.window}_{std_str}"]

    def generate_signals(self, df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        std_str = str(self.num_std).replace(".", "p")
        prefix = f"bb_{self.window}_{std_str}"
        lower_col = f"{prefix}_lower"
        upper_col = f"{prefix}_upper"
        logger.debug(f"Generating Bollinger signals (window={self.window}, std={self.num_std})")

        entries = (df["close"] <= df[lower_col]).fillna(False)
        exits = (df["close"] >= df[upper_col]).fillna(False)

        logger.debug(f"Bollinger signals: {entries.sum()} entries, {exits.sum()} exits")
        return entries, exits

    @classmethod
    def get_variants(cls):
        return [cls(window=w, num_std=s) for w, s in config.BOLLINGER_PARAMS]
