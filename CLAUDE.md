# Trading Engine - System Prompt & Build Instructions

## Overview
This is a modular trading engine that:
1. Fetches historical price data from Binance (cached to CSV)
2. Calculates technical indicators with parameterized variants (parameter sweep)
3. Generates trading signals from modular, composable rules
4. Runs backtests via vectorbt in parallel (ThreadPoolExecutor)
5. Applies a pass/fail filter (max drawdown threshold) on in-sample data (60%)
6. Re-tests survivors on out-of-sample data (40%)
7. Visualizes final survivors in a dashboard with equity curves, drawdown charts, and stats

## Architecture

```
project/
├── CLAUDE.md              # This file - system prompt & instructions
├── config.py              # All configuration (symbols, timeframes, thresholds, param grids)
├── data_fetcher.py        # Binance data fetching + CSV caching + train/test split
├── data_cache/            # CSV cache dir (auto-created, avoids re-downloading)
├── indicators/            # Modular indicator library (parameterized)
│   ├── __init__.py        # Registry - auto-discovers indicators, supports get_variants()
│   ├── base.py            # Base class for all indicators
│   ├── rsi.py             # RSI indicator (variants per period)
│   ├── sma_cross.py       # SMA crossover indicator (variants per period pair)
│   ├── macd.py            # MACD indicator (variants per param set)
│   ├── ema.py             # EMA crossover indicator (variants per period pair)
│   └── bollinger.py       # Bollinger Bands indicator (variants per window/std)
├── rules/                 # Modular trading rules (signal generators, parameterized)
│   ├── __init__.py        # Registry - auto-discovers rules, supports get_variants()
│   ├── base.py            # Base class for all rules
│   ├── rsi_oversold.py    # Buy RSI oversold, sell overbought (period x threshold combos)
│   ├── sma_cross_rule.py  # Buy golden cross, sell death cross (per period pair)
│   ├── macd_cross_rule.py # Buy/sell on MACD signal crossover (per param set)
│   ├── ema_cross_rule.py  # Buy/sell on EMA crossover (per period pair)
│   └── bollinger_rule.py  # Buy at lower band, sell at upper band (per window/std)
├── engine.py              # Core backtest engine (vectorbt integration)
├── pipeline.py            # Full pipeline with parallel execution (ThreadPoolExecutor)
├── dashboard.py           # Plotly dashboard for surviving strategies
├── main.py                # Entry point - run everything
├── requirements.txt       # Dependencies
└── logs/                  # Debug logs written here
```

## Parameter Sweep System
Each indicator and rule class can define a `get_variants()` classmethod that returns
multiple instances with different parameters. The registry auto-registers all variants.

Parameter grids are defined in `config.py`:
- `RSI_PERIODS` + `RSI_THRESHOLDS` → RSI period x threshold combos
- `SMA_PERIODS` → SMA fast/slow period pairs
- `EMA_PERIODS` → EMA fast/slow period pairs
- `MACD_PARAMS` → MACD (fast, slow, signal) tuples
- `BOLLINGER_PARAMS` → Bollinger (window, num_std) pairs

Each variant gets a unique name (e.g. `RSI(14) <30 >70`) and unique column names
(e.g. `rsi_14`) so they don't collide when multiple indicators run on the same DataFrame.

## How Indicators Work (Modular Plugin System)
- Every indicator lives in `indicators/` as its own `.py` file
- Each must subclass `BaseIndicator` from `indicators/base.py`
- Must implement `name` property and `compute(df) -> df` method
- Optional: implement `get_variants()` classmethod to return parameter sweep instances
- The `compute` method receives OHLCV DataFrame and adds uniquely-named columns
- The `indicators/__init__.py` auto-discovers all subclasses - just drop in a new file

### Adding a New Indicator
1. Create `indicators/my_indicator.py`
2. Subclass `BaseIndicator`
3. Implement `name` (include params for uniqueness) and `compute(df)`
4. Optionally implement `get_variants()` to define parameter sweep
5. Done. The registry picks it up automatically.

## How Trading Rules Work (Modular Plugin System)
- Every rule lives in `rules/` as its own `.py` file
- Each must subclass `BaseRule` from `rules/base.py`
- Must implement `name`, `required_indicators`, and `generate_signals(df) -> (entries, exits)`
- Optional: implement `get_variants()` classmethod to return parameter sweep instances
- `required_indicators` returns list of indicator names this rule depends on
- Rules can be stacked/combined - the engine runs combos (AND/OR logic)

### Adding a New Rule
1. Create `rules/my_rule.py`
2. Subclass `BaseRule`
3. Implement `name`, `required_indicators`, and `generate_signals(df)`
4. Optionally implement `get_variants()` to define parameter sweep
5. Done. The registry picks it up automatically.

### Combining Rules (Combos)
- The engine supports combining multiple rules with AND logic (all must agree to enter)
- Exit uses OR logic (any rule triggers exit)
- `COMBO_MAX_SIZE` in config controls max rules per combo
- This lets you stack e.g. "RSI oversold AND SMA golden cross" without writing new code

## Pass/Fail Metric
- **Metric**: Maximum Drawdown
- **In-Sample threshold**: configurable in `config.py` (default: max drawdown < 30%)
- **Out-of-Sample**: same threshold applied to survivors
- Strategies that exceed max drawdown in either phase are eliminated

## Pipeline Flow
```
1. Fetch Binance OHLCV data (cached to CSV)
2. Split 60% train (in-sample) / 40% test (out-of-sample)
3. Generate all rule variants from parameter grids
4. Build combos (singles, pairs, etc.) from all rule variants
5. For each combo (in parallel via ThreadPoolExecutor):
   a. Compute required indicators on training data
   b. Generate entry/exit signals
   c. Run vectorbt backtest
   d. Check if max_drawdown < threshold → PASS/FAIL
6. Collect all passing strategies (survivors)
7. For each survivor (in parallel):
   a. Compute indicators on test data
   b. Generate signals
   c. Run vectorbt backtest
   d. Check max_drawdown again → final PASS/FAIL
8. Display dashboard of final survivors with equity curves & stats
```

## Configuration (config.py)
```python
SYMBOL = "BTCUSDT"
TIMEFRAME = "1h"
LOOKBACK_DAYS = 365
CSV_CACHE_DIR = "data_cache"
TRAIN_RATIO = 0.6
MAX_DRAWDOWN_THRESHOLD = 0.30
COMBO_MAX_SIZE = 2
INITIAL_CAPITAL = 10000
FEES = 0.001
PARALLEL_WORKERS = 8

# Parameter grids
RSI_PERIODS = [10, 14, 21]
RSI_THRESHOLDS = [(20, 80), (25, 75), (30, 70)]
SMA_PERIODS = [(10, 30), (20, 50), (20, 100), (50, 200)]
EMA_PERIODS = [(5, 13), (9, 21), (9, 50), (12, 26), (20, 50)]
MACD_PARAMS = [(12, 26, 9)]
BOLLINGER_PARAMS = [(20, 2.0), (20, 1.5), (30, 2.0)]
```

## Dashboard
- Uses Plotly Dash with dark theme
- Stats bar: combos tested, IS survivors, final survivors, best OOS return, lowest DD
- Strategy selector dropdown (multi-select, defaults to top 5)
- Side-by-side OOS and IS charts with equity curve on top (70%) and drawdown fill below (30%)
- Survivors table: sortable, color-coded, paginated, with IS/OOS metrics
- Auto-opens in browser at http://127.0.0.1:8050

## Build & Run Instructions

### For Claude (self-instructions):
1. Build all files following this architecture exactly
2. Add comprehensive debug logging (Python `logging` module) to EVERY function
3. Log levels: DEBUG for data shapes/values, INFO for pipeline steps, WARNING for issues, ERROR for failures
4. All logs go to both console (INFO+) and `logs/engine.log` (DEBUG+)
5. After building, run `main.py` with: `python main.py`
6. If there are errors, read the full traceback, fix the issue, and re-run
7. Keep iterating until it runs clean end-to-end
8. The dashboard should open and display results

### For Users:
```bash
pip install -r requirements.txt
python main.py
```

## Dependencies
- `python-binance` - Binance API (no API key needed for public kline data)
- `vectorbt` - Backtesting engine
- `pandas` / `numpy` - Data manipulation
- `ta` - Technical analysis indicators library
- `plotly` / `dash` - Dashboard visualization
- `requests` - HTTP requests (Binance REST fallback)

## Debug Logging Strategy
- Every function entry/exit logged at DEBUG
- Data shapes logged after every transform
- Indicator values (head/tail) logged after computation
- Signal counts logged (how many entries/exits generated)
- Backtest results logged (return, drawdown, sharpe)
- Pass/fail decisions logged at INFO
- Errors logged with full context at ERROR
- Pipeline timing and worker counts logged at INFO

## Key Design Principles
- **Modularity**: Drop in new indicators/rules without touching existing code
- **Composability**: Rules can be combined into combos automatically
- **Parameter Sweep**: Each indicator/rule can define parameter variants via get_variants()
- **CSV Caching**: Data fetched once, then loaded from CSV on repeat runs
- **Parallel Execution**: Backtests run in parallel via ThreadPoolExecutor
- **Transparency**: Every step logged so you can trace exactly what happened
- **Reproducibility**: Same config = same results (no randomness)
- **Fail-fast**: Clear error messages if data fetch fails or indicators can't compute
