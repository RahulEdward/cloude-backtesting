"""
RSI Oversold/Overbought rule.
Generates variants for each RSI period x threshold combo.
"""

import logging

import pandas as pd

from rules import register
from rules.base import BaseRule
import config

logger = logging.getLogger(__name__)


@register
class RSIOversoldRule(BaseRule):

    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    @property
    def name(self) -> str:
        return f"RSI({self.period}) <{int(self.oversold)} >{int(self.overbought)}"

    @property
    def required_indicators(self) -> list[str]:
        return [f"rsi_{self.period}"]

    def generate_signals(self, df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        col = f"rsi_{self.period}"
        logger.debug(f"Generating RSI signals (period={self.period}, os={self.oversold}, ob={self.overbought})")
        entries = (df[col] < self.oversold).fillna(False)
        exits = (df[col] > self.overbought).fillna(False)
        logger.debug(f"RSI signals: {entries.sum()} entries, {exits.sum()} exits")
        return entries, exits

    @classmethod
    def get_variants(cls):
        variants = []
        for period in config.RSI_PERIODS:
            for oversold, overbought in config.RSI_THRESHOLDS:
                variants.append(cls(period=period, oversold=oversold, overbought=overbought))
        return variants
