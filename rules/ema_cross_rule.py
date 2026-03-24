"""
EMA Crossover rule.
Buy when fast EMA crosses above slow EMA, sell when below.
Generates variants for each EMA period pair.
"""

import logging

import pandas as pd

from rules import register
from rules.base import BaseRule
import config

logger = logging.getLogger(__name__)


@register
class EMACrossRule(BaseRule):

    def __init__(self, fast_period: int = 9, slow_period: int = 21):
        self.fast_period = fast_period
        self.slow_period = slow_period

    @property
    def name(self) -> str:
        return f"EMA Cross({self.fast_period}/{self.slow_period})"

    @property
    def required_indicators(self) -> list[str]:
        return [f"ema_{self.fast_period}_{self.slow_period}"]

    def generate_signals(self, df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        fast_col = f"ema_fast_{self.fast_period}_{self.slow_period}"
        slow_col = f"ema_slow_{self.fast_period}_{self.slow_period}"
        logger.debug(f"Generating EMA cross signals ({self.fast_period}/{self.slow_period})")

        fast_above = df[fast_col] > df[slow_col]
        prev = fast_above.shift(1).fillna(False).infer_objects(copy=False)

        entries = (fast_above & ~prev).fillna(False)
        exits = (~fast_above & prev).fillna(False)

        logger.debug(f"EMA cross signals: {entries.sum()} entries, {exits.sum()} exits")
        return entries, exits

    @classmethod
    def get_variants(cls):
        return [cls(fast_period=f, slow_period=s) for f, s in config.EMA_PERIODS]
