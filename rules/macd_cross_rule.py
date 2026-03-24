"""
MACD Crossover rule.
Buy when MACD crosses above signal, sell when below.
Generates variants for each MACD param set.
"""

import logging

import pandas as pd

from rules import register
from rules.base import BaseRule
import config

logger = logging.getLogger(__name__)


@register
class MACDCrossRule(BaseRule):

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    @property
    def name(self) -> str:
        return f"MACD Cross({self.fast}/{self.slow}/{self.signal})"

    @property
    def required_indicators(self) -> list[str]:
        return [f"macd_{self.fast}_{self.slow}_{self.signal}"]

    def generate_signals(self, df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        prefix = f"macd_{self.fast}_{self.slow}_{self.signal}"
        line_col = f"{prefix}_line"
        sig_col = f"{prefix}_signal"
        logger.debug(f"Generating MACD cross signals ({self.fast}/{self.slow}/{self.signal})")

        macd_above = df[line_col] > df[sig_col]
        prev = macd_above.shift(1).fillna(False).infer_objects(copy=False)

        entries = (macd_above & ~prev).fillna(False)
        exits = (~macd_above & prev).fillna(False)

        logger.debug(f"MACD cross signals: {entries.sum()} entries, {exits.sum()} exits")
        return entries, exits

    @classmethod
    def get_variants(cls):
        return [cls(fast=f, slow=s, signal=sig) for f, s, sig in config.MACD_PARAMS]
