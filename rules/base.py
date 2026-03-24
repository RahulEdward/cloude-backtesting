"""
Base class for all trading rules.
"""

from abc import ABC, abstractmethod

import pandas as pd


class BaseRule(ABC):
    """
    All rules must subclass this and implement:
    - name: unique string identifier
    - required_indicators: list of indicator names this rule needs
    - generate_signals(df): return (entries, exits) as boolean Series
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this rule."""
        ...

    @property
    @abstractmethod
    def required_indicators(self) -> list[str]:
        """List of indicator names that must be computed before this rule runs."""
        ...

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        """
        Generate entry and exit signals.
        Returns: (entries, exits) - both boolean pd.Series aligned with df index.
        """
        ...

    def __repr__(self):
        return f"<Rule: {self.name}>"
