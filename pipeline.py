"""
Full pipeline: generate strategy combos, run in-sample, filter, run out-of-sample.
Supports parallel execution via ThreadPoolExecutor.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import combinations

import pandas as pd

import config
import indicators as ind_registry
import rules as rule_registry
from engine import run_backtest

logger = logging.getLogger(__name__)


def compute_indicators_for_rules(df: pd.DataFrame, rule_list: list) -> pd.DataFrame:
    """Compute all indicators required by the given rules."""
    df = df.copy()
    needed = set()
    for rule in rule_list:
        needed.update(rule.required_indicators)

    logger.debug(f"Indicators needed: {needed}")

    for ind_name in needed:
        indicator = ind_registry.get_indicator(ind_name)
        df = indicator.compute(df)
        logger.debug(f"Computed indicator: {ind_name}")

    return df


def generate_combo_signals(df: pd.DataFrame, rule_list: list) -> tuple[pd.Series, pd.Series]:
    """
    Combine multiple rules with AND logic.
    Entry = all rules say enter. Exit = any rule says exit.
    """
    all_entries = []
    all_exits = []

    for rule in rule_list:
        entries, exits = rule.generate_signals(df)
        all_entries.append(entries)
        all_exits.append(exits)

    combined_entries = all_entries[0]
    for e in all_entries[1:]:
        combined_entries = combined_entries & e

    combined_exits = all_exits[0]
    for x in all_exits[1:]:
        combined_exits = combined_exits | x

    logger.debug(
        f"Combined signals: {combined_entries.sum()} entries, {combined_exits.sum()} exits"
    )

    return combined_entries, combined_exits


def build_strategy_combos() -> list[tuple[str, list]]:
    """
    Build all strategy combinations up to COMBO_MAX_SIZE.
    Returns list of (name, [rule_instances]).
    """
    all_rules = rule_registry.get_all_rules()
    combos = []

    for size in range(1, config.COMBO_MAX_SIZE + 1):
        for combo in combinations(all_rules, size):
            name = " + ".join(r.name for r in combo)
            combos.append((name, list(combo)))

    logger.info(f"Built {len(combos)} strategy combos from {len(all_rules)} rules")
    return combos


def _run_single_strategy(name, rule_list, df):
    """Run a single strategy backtest. Used by ThreadPoolExecutor."""
    try:
        df_with_indicators = compute_indicators_for_rules(df, rule_list)
        entries, exits = generate_combo_signals(df_with_indicators, rule_list)
        result = run_backtest(df_with_indicators, entries, exits, strategy_name=name)
        result["rules"] = rule_list
        return result
    except Exception as e:
        logger.error(f"Strategy '{name}' failed: {e}", exc_info=True)
        return None


def run_pipeline(train_df: pd.DataFrame, test_df: pd.DataFrame) -> tuple[list[dict], dict]:
    """
    Full pipeline:
    1. Build all strategy combos
    2. Run each on in-sample data (parallel)
    3. Filter survivors (pass drawdown threshold)
    4. Run survivors on out-of-sample data (parallel)
    5. Return final results + pipeline stats
    """
    logger.info("=" * 60)
    logger.info("STARTING PIPELINE")
    logger.info("=" * 60)

    combos = build_strategy_combos()

    # ── Phase 1: In-Sample (parallel) ──
    logger.info("-" * 40)
    logger.info(f"PHASE 1: IN-SAMPLE TESTING ({len(combos)} combos, {config.PARALLEL_WORKERS} workers)")
    logger.info("-" * 40)

    in_sample_results = []
    with ThreadPoolExecutor(max_workers=config.PARALLEL_WORKERS) as executor:
        futures = {}
        for name, rule_list in combos:
            future = executor.submit(_run_single_strategy, name, rule_list, train_df)
            futures[future] = name

        for future in as_completed(futures):
            name = futures[future]
            result = future.result()
            if result is not None:
                result["phase"] = "in_sample"
                in_sample_results.append(result)

    survivors = [r for r in in_sample_results if r["passed"]]
    failed = [r for r in in_sample_results if not r["passed"]]

    logger.info(
        f"In-sample results: {len(survivors)} PASSED, {len(failed)} FAILED "
        f"out of {len(in_sample_results)}"
    )

    if not survivors:
        logger.warning("No strategies survived in-sample phase!")
        stats = {
            "combos_tested": len(combos),
            "is_survivors": 0,
            "final_survivors": 0,
            "total_oos_tested": 0,
            "best_oos_return": 0.0,
            "lowest_oos_drawdown": 0.0,
        }
        return [], stats

    # ── Phase 2: Out-of-Sample (parallel) ──
    logger.info("-" * 40)
    logger.info(f"PHASE 2: OUT-OF-SAMPLE TESTING ({len(survivors)} survivors)")
    logger.info("-" * 40)

    final_results = []
    with ThreadPoolExecutor(max_workers=config.PARALLEL_WORKERS) as executor:
        futures = {}
        for survivor in survivors:
            name = survivor["strategy"]
            rule_list = survivor["rules"]
            future = executor.submit(_run_single_strategy, name, rule_list, test_df)
            futures[future] = survivor

        for future in as_completed(futures):
            survivor = futures[future]
            oos_result = future.result()
            if oos_result is None:
                continue

            name = survivor["strategy"]
            final_results.append({
                "strategy": name,
                "in_sample": {
                    "total_return": survivor["total_return"],
                    "max_drawdown": survivor["max_drawdown"],
                    "sharpe_ratio": survivor["sharpe_ratio"],
                    "sortino_ratio": survivor.get("sortino_ratio", 0.0),
                    "win_rate": survivor["win_rate"],
                    "num_trades": survivor["num_trades"],
                    "passed": survivor["passed"],
                    "portfolio": survivor["portfolio"],
                },
                "out_of_sample": {
                    "total_return": oos_result["total_return"],
                    "max_drawdown": oos_result["max_drawdown"],
                    "sharpe_ratio": oos_result["sharpe_ratio"],
                    "sortino_ratio": oos_result.get("sortino_ratio", 0.0),
                    "win_rate": oos_result["win_rate"],
                    "num_trades": oos_result["num_trades"],
                    "passed": oos_result["passed"],
                    "portfolio": oos_result["portfolio"],
                },
                "final_passed": survivor["passed"] and oos_result["passed"],
            })

    final_survivors = [r for r in final_results if r["final_passed"]]
    logger.info(
        f"Final results: {len(final_survivors)} survived both phases "
        f"out of {len(final_results)} tested"
    )

    pipeline_stats = {
        "combos_tested": len(combos),
        "is_survivors": len(survivors),
        "final_survivors": len(final_survivors),
        "total_oos_tested": len(final_results),
    }

    if final_survivors:
        pipeline_stats["best_oos_return"] = max(
            r["out_of_sample"]["total_return"] for r in final_survivors
        )
        pipeline_stats["lowest_oos_drawdown"] = min(
            abs(r["out_of_sample"]["max_drawdown"]) for r in final_survivors
        )
    else:
        pipeline_stats["best_oos_return"] = 0.0
        pipeline_stats["lowest_oos_drawdown"] = 0.0

    return final_results, pipeline_stats
