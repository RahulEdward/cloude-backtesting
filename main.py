"""
Entry point for the trading engine.
Fetches data, runs pipeline, launches dashboard.
"""

import logging
import os
import sys

import config
from data_fetcher import get_data
from pipeline import run_pipeline
from dashboard import launch_dashboard


def setup_logging():
    """Configure logging to console and file."""
    os.makedirs(config.LOG_DIR, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler (INFO+)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(getattr(logging, config.LOG_LEVEL_CONSOLE))
    console.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    ))
    root_logger.addHandler(console)

    # File handler (DEBUG+)
    file_handler = logging.FileHandler(config.LOG_FILE, mode="w", encoding="utf-8")
    file_handler.setLevel(getattr(logging, config.LOG_LEVEL_FILE))
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
    ))
    root_logger.addHandler(file_handler)


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("TRADING ENGINE STARTING")
    logger.info(f"Symbol: {config.SYMBOL}, Timeframe: {config.TIMEFRAME}")
    logger.info(f"Lookback: {config.LOOKBACK_DAYS} days, Split: {config.TRAIN_RATIO:.0%}/{1-config.TRAIN_RATIO:.0%}")
    logger.info(f"Max Drawdown Threshold: {config.MAX_DRAWDOWN_THRESHOLD:.0%}")
    logger.info("=" * 60)

    # Step 1: Fetch data
    logger.info("Step 1: Fetching data from Binance")
    train_df, test_df = get_data()

    # Step 2: Run pipeline
    logger.info("Step 2: Running backtest pipeline")
    results, pipeline_stats = run_pipeline(train_df, test_df)

    # Step 3: Print summary
    final_survivors = [r for r in results if r["final_passed"]]
    logger.info("=" * 60)
    logger.info(f"PIPELINE COMPLETE: {len(final_survivors)} final survivors out of {len(results)} tested")
    for r in results:
        status = "PASS" if r["final_passed"] else "FAIL"
        logger.info(
            f"  [{status}] {r['strategy']}: "
            f"IS return={r['in_sample']['total_return']:.2%} dd={r['in_sample']['max_drawdown']:.2%} | "
            f"OOS return={r['out_of_sample']['total_return']:.2%} dd={r['out_of_sample']['max_drawdown']:.2%}"
        )
    logger.info("=" * 60)

    # Step 4: Launch dashboard (only final survivors)
    logger.info("Step 3: Launching dashboard")
    launch_dashboard(results, pipeline_stats)


if __name__ == "__main__":
    main()
