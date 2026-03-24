"""
Base class for all indicators.
"""

from abc import ABC, abstractmethod

import pandas as pd


class BaseIndicator(ABC):
    """
    All indicators must subclass this and implement:
    - name: unique string identifier
    - compute(df): add indicator columns to the OHLCV dataframe
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this indicator."""
        ...

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute the indicator and add columns to df.
        Must return the modified DataFrame.
        """
        ...

    def __repr__(self):
        return f"<Indicator: {self.name}>"
