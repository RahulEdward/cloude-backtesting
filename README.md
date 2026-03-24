<div align="center">

# Autonomous Backtesting Engine

**Walk-forward validated strategy discovery with automated parameter sweeps**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![vectorbt](https://img.shields.io/badge/Engine-vectorbt-00C853)](https://vectorbt.dev)
[![Dash](https://img.shields.io/badge/Dashboard-Plotly%20Dash-119DFF?logo=plotly)](https://dash.plotly.com)
[![Binance](https://img.shields.io/badge/Crypto-Binance%20API-F0B90B?logo=binance)](https://binance.com)
[![Yahoo Finance](https://img.shields.io/badge/Stocks%20%26%20Forex-Yahoo%20Finance-720e9e)](https://finance.yahoo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<br>

*Fetches market data, sweeps parameter grids across technical indicators, backtests hundreds of strategy combinations in parallel, filters by max drawdown on both in-sample and out-of-sample data, and visualizes survivors in a real-time dashboard.*

<br>

</div>

---

## Overview

Most backtesting results are lies. A strategy that looks great on historical data often fails on new data because it was **overfit** to the past.

This engine solves that problem using **walk-forward validation**:

1. Train on 60% of data (in-sample) → find strategies that work
2. Test survivors on 40% unseen data (out-of-sample) → filter out lucky ones
3. Only strategies that pass **both** phases survive

The result: strategies with a statistically meaningful edge, not just curve-fitted flukes.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Parameter Sweep** | Automatically tests hundreds of parameter combinations across multiple indicator types |
| **Walk-Forward Validation** | 60/40 in-sample/out-of-sample split prevents overfitting |
| **Parallel Execution** | ThreadPoolExecutor runs backtests across all CPU cores simultaneously |
| **Plugin Architecture** | Drop a `.py` file in `indicators/` or `rules/` — auto-discovered, zero config |
| **CSV Caching** | Data fetched once from Binance, then loaded instantly from disk |
| **Dark-Theme Dashboard** | Professional Plotly Dash UI with equity curves, drawdown charts, and sortable tables |
| **Combo Stacking** | Automatically combines rules (AND logic for entries, OR for exits) |

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/RahulEdward/cloude-backtesting.git
cd cloude-backtesting

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the engine
python main.py
```

The dashboard auto-opens at **http://127.0.0.1:8050**

> **Note:** No Binance API key required. Uses the free public kline endpoint.

---

## How It Works

```
              ┌──────────────────────────────────────────┐
              │           Multi-Market Data Source        │
              │                                          │
              │  Crypto  → Binance REST API (no key)     │
              │  Stocks  → Yahoo Finance (yfinance)      │
              │  Forex   → Yahoo Finance (yfinance)      │
              └──────────────────┬───────────────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────────────┐
              │            CSV Cache Layer                │
              │         (instant on re-run)               │
              └──────────────────┬───────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
             ┌─────────────┐          ┌─────────────┐
             │  In-Sample  │          │Out-of-Sample│
             │    (60%)    │          │    (40%)    │
             └──────┬──────┘          └──────┬──────┘
                    │                        │
                    ▼                        │
        ┌───────────────────────┐            │
        │   Parameter Sweep     │            │
        │  ─────────────────    │            │
        │  22 rule variants     │            │
        │  × combo pairs        │            │
        │  = 253 strategies     │            │
        └───────────┬───────────┘            │
                    │                        │
                    ▼                        │
        ┌───────────────────────┐            │
        │   Parallel Backtest   │            │
        │   (8 threads)         │            │
        └───────────┬───────────┘            │
                    │                        │
                    ▼                        │
        ┌───────────────────────┐            │
        │   Max DD < 30%?       │            │
        │   FAIL → eliminated   │            │
        │   PASS → survivors    │            │
        └───────────┬───────────┘            │
                    │                        │
                    └────────────┬────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────┐
              │   Re-test on OOS data        │
              │   Same DD filter applied     │
              └──────────────┬───────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    ▼                 ▼
             ┌──────────┐      ┌──────────┐
             │   PASS   │      │   FAIL   │
             │Dashboard │      │Eliminated│
             └──────────┘      └──────────┘
```

---

## Parameter Sweep

The engine generates **22 individual strategy variants** from 5 indicator types, then builds **all pairwise combinations** for 253 total strategies:

| Indicator | Parameters Swept | Variants |
|-----------|-----------------|----------|
| **RSI** | Periods `[10, 14, 21]` × Thresholds `[(20,80), (25,75), (30,70)]` | 9 |
| **SMA Cross** | Period pairs `[(10,30), (20,50), (20,100), (50,200)]` | 4 |
| **EMA Cross** | Period pairs `[(5,13), (9,21), (9,50), (12,26), (20,50)]` | 5 |
| **MACD** | Standard `(12, 26, 9)` | 1 |
| **Bollinger Bands** | `(window, std)` = `[(20,2.0), (20,1.5), (30,2.0)]` | 3 |

**Total:** 22 singles + 231 pairs = **253 combos tested**

---

## Project Structure

```
cloude-backtesting/
│
├── config.py                 # All settings & parameter grids
├── data_fetcher.py           # Binance API client + CSV caching + train/test split
│
├── indicators/               # Technical indicator plugins (auto-discovered)
│   ├── __init__.py           # Registry with get_variants() support
│   ├── base.py               # BaseIndicator abstract class
│   ├── rsi.py                # Relative Strength Index
│   ├── sma_cross.py          # Simple Moving Average crossover
│   ├── ema.py                # Exponential Moving Average crossover
│   ├── macd.py               # MACD line + signal
│   └── bollinger.py          # Bollinger Bands (upper/mid/lower)
│
├── rules/                    # Trading signal plugins (auto-discovered)
│   ├── __init__.py           # Registry with get_variants() support
│   ├── base.py               # BaseRule abstract class
│   ├── rsi_oversold.py       # Buy oversold, sell overbought
│   ├── sma_cross_rule.py     # Golden cross / death cross
│   ├── ema_cross_rule.py     # EMA crossover signals
│   ├── macd_cross_rule.py    # MACD signal line crossover
│   └── bollinger_rule.py     # Buy at lower band, sell at upper
│
├── engine.py                 # vectorbt portfolio simulation
├── pipeline.py               # Orchestration: sweep → backtest → filter → validate
├── dashboard.py              # Plotly Dash dark-theme dashboard
├── main.py                   # Entry point
│
├── data_cache/               # CSV cache (auto-created, gitignored)
├── logs/                     # Debug logs (auto-created, gitignored)
└── requirements.txt          # Python dependencies
```

---

## Configuration

All settings in one file — `config.py`:

```python
# ── Data ──
SYMBOL = "BTCUSDT"              # Any Binance trading pair
TIMEFRAME = "1h"                # 1m, 5m, 15m, 1h, 4h, 1d
LOOKBACK_DAYS = 365             # Historical data period

# ── Validation ──
TRAIN_RATIO = 0.6               # 60% in-sample / 40% out-of-sample
MAX_DRAWDOWN_THRESHOLD = 0.30   # Max 30% drawdown = fail

# ── Execution ──
INITIAL_CAPITAL = 10000         # Starting portfolio ($)
FEES = 0.001                    # 0.1% per trade
COMBO_MAX_SIZE = 2              # Max rules per combo (1=singles, 2=pairs, 3=triples)
PARALLEL_WORKERS = 8            # Concurrent backtest threads

# ── Parameter Grids ──
RSI_PERIODS = [10, 14, 21]
RSI_THRESHOLDS = [(20, 80), (25, 75), (30, 70)]
SMA_PERIODS = [(10, 30), (20, 50), (20, 100), (50, 200)]
EMA_PERIODS = [(5, 13), (9, 21), (9, 50), (12, 26), (20, 50)]
MACD_PARAMS = [(12, 26, 9)]
BOLLINGER_PARAMS = [(20, 2.0), (20, 1.5), (30, 2.0)]
```

---

## Extending the Engine

The plugin system makes it trivial to add new indicators and rules. Just drop a file — no imports, no registration, no config changes needed.

### Adding a New Indicator

Create `indicators/dema.py`:

```python
from indicators import register
from indicators.base import BaseIndicator
import config

@register
class DEMAIndicator(BaseIndicator):
    def __init__(self, period=21):
        self.period = period

    @property
    def name(self):
        return f"dema_{self.period}"

    def compute(self, df):
        ema1 = df["close"].ewm(span=self.period, adjust=False).mean()
        ema2 = ema1.ewm(span=self.period, adjust=False).mean()
        df[f"dema_{self.period}"] = 2 * ema1 - ema2
        return df

    @classmethod
    def get_variants(cls):
        return [cls(period=p) for p in [14, 21, 50]]
```

### Adding a New Rule

Create `rules/dema_rule.py`:

```python
from rules import register
from rules.base import BaseRule

@register
class DEMACrossRule(BaseRule):
    def __init__(self, period=21):
        self.period = period

    @property
    def name(self):
        return f"DEMA Cross({self.period})"

    @property
    def required_indicators(self):
        return [f"dema_{self.period}"]

    def generate_signals(self, df):
        col = f"dema_{self.period}"
        above = (df["close"] > df[col])
        prev = above.shift(1).fillna(False)
        entries = (above & ~prev).fillna(False)
        exits = (~above & prev).fillna(False)
        return entries, exits

    @classmethod
    def get_variants(cls):
        return [cls(period=p) for p in [14, 21, 50]]
```

**That's it.** Run `python main.py` — the new strategies are automatically included in the sweep.

---

## Dashboard

The dashboard provides real-time visualization of surviving strategies:

- **Stats Bar** — Combos tested, IS survivors, final survivors, best OOS return, lowest drawdown
- **Strategy Selector** — Multi-select dropdown to compare any combination of strategies
- **Equity Curves** — Side-by-side Out-of-Sample and In-Sample charts with drawdown overlay
- **Results Table** — Sortable by any column, color-coded rankings (gold/silver/bronze), paginated
- **Metrics** — Return, Max Drawdown, Sharpe Ratio, Sortino Ratio, Win Rate, Trade Count

---

## Logging

Comprehensive logging at two levels:

| Output | Level | What's Logged |
|--------|-------|--------------|
| Console | `INFO+` | Pipeline steps, pass/fail decisions, survivor counts |
| `logs/engine.log` | `DEBUG+` | Data shapes, indicator values, signal counts, full tracebacks |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backtesting Engine | [vectorbt](https://vectorbt.dev) |
| Technical Indicators | [ta](https://github.com/bukosabino/ta) |
| Crypto Data | [Binance REST API](https://binance-docs.github.io/apidocs/) (public, no key) |
| Stocks & Forex Data | [Yahoo Finance](https://finance.yahoo.com) via [yfinance](https://github.com/ranaroussi/yfinance) |
| Dashboard | [Plotly Dash](https://dash.plotly.com) |
| Data Processing | pandas, numpy |
| Parallelism | concurrent.futures.ThreadPoolExecutor |

---

## Requirements

- Python 3.10+
- Internet connection (first run only — data is cached)
- ~500MB RAM for 253 strategy backtests

```
pandas>=1.5.0
numpy>=1.23.0
vectorbt>=0.26.0
ta>=0.10.0
plotly>=5.0.0
dash>=2.0.0
requests>=2.28.0
```

---

## License

MIT

---

<div align="center">

**Built with [vectorbt](https://vectorbt.dev) + [Plotly Dash](https://dash.plotly.com)**

</div>
