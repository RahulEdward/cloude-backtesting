"""
Core backtest engine using vectorbt.
Takes signals and runs them through vectorbt's portfolio simulation.
"""

import logging

import numpy as np
import pandas as pd
import vectorbt as vbt

import config

logger = logging.getLogger(__name__)


def run_backtest(
    df: pd.DataFrame,
    entries: pd.Series,
    exits: pd.Series,
    strategy_name: str = "unnamed",
) -> dict:
    """
    Run a single backtest using vectorbt.

    Args:
        df: OHLCV DataFrame
        entries: Boolean Series of entry signals
        exits: Boolean Series of exit signals
        strategy_name: Name for logging

    Returns:
        dict with backtest results including pass/fail status
    """
    logger.info(f"Running backtest for '{strategy_name}'")
    logger.debug(f"Data shape: {df.shape}, entries: {entries.sum()}, exits: {exits.sum()}")

    # Ensure entries and exits are boolean and aligned with df
    entries = entries.reindex(df.index).fillna(False).astype(bool)
    exits = exits.reindex(df.index).fillna(False).astype(bool)

    if entries.sum() == 0:
        logger.warning(f"Strategy '{strategy_name}' has ZERO entry signals - marking as FAIL")
        return {
            "strategy": strategy_name,
            "total_return": 0.0,
            "max_drawdown": 1.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "win_rate": 0.0,
            "num_trades": 0,
            "passed": False,
            "portfolio": None,
        }

    try:
        portfolio = vbt.Portfolio.from_signals(
            close=df["close"],
            entries=entries,
            exits=exits,
            init_cash=config.INITIAL_CAPITAL,
            fees=config.FEES,
            freq="1h",
        )

        total_return = portfolio.total_return()
        max_dd = portfolio.max_drawdown()
        num_trades = portfolio.trades.count()

        # Sharpe ratio - handle edge cases
        try:
            sharpe = portfolio.sharpe_ratio()
            if np.isnan(sharpe) or np.isinf(sharpe):
                sharpe = 0.0
        except Exception:
            sharpe = 0.0

        # Sortino ratio
        try:
            sortino = portfolio.sortino_ratio()
            if np.isnan(sortino) or np.isinf(sortino):
                sortino = 0.0
        except Exception:
            sortino = 0.0

        # Win rate
        try:
            if num_trades > 0:
                win_rate = portfolio.trades.win_rate()
                if np.isnan(win_rate):
                    win_rate = 0.0
            else:
                win_rate = 0.0
        except Exception:
            win_rate = 0.0

        passed = abs(max_dd) < config.MAX_DRAWDOWN_THRESHOLD

        logger.info(
            f"Strategy '{strategy_name}': return={total_return:.4f}, "
            f"max_dd={max_dd:.4f}, sharpe={sharpe:.4f}, sortino={sortino:.4f}, "
            f"trades={num_trades}, win_rate={win_rate:.4f}, "
            f"{'PASS' if passed else 'FAIL'}"
        )

        return {
            "strategy": strategy_name,
            "total_return": float(total_return),
            "max_drawdown": float(max_dd),
            "sharpe_ratio": float(sharpe),
            "sortino_ratio": float(sortino),
            "win_rate": float(win_rate),
            "num_trades": int(num_trades),
            "passed": passed,
            "portfolio": portfolio,
        }

    except Exception as e:
        logger.error(f"Backtest failed for '{strategy_name}': {e}", exc_info=True)
        return {
            "strategy": strategy_name,
            "total_return": 0.0,
            "max_drawdown": 1.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "win_rate": 0.0,
            "num_trades": 0,
            "passed": False,
            "portfolio": None,
        }
