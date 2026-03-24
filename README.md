# Backtest Trading Engine

A modular, automated backtesting engine that fetches live market data from Binance, runs parameterized strategy sweeps through vectorbt, and filters results using walk-forward validation (in-sample/out-of-sample) with a max-drawdown pass/fail gate.

## What It Does

1. **Fetches** historical OHLCV candlestick data from Binance (cached to CSV)
2. **Splits** data 60/40 into training (in-sample) and testing (out-of-sample) sets
3. **Generates** hundreds of strategy variants via parameter sweeps across indicators
4. **Backtests** all variants in parallel using vectorbt + ThreadPoolExecutor
5. **Filters** strategies by max drawdown threshold on in-sample data
6. **Validates** survivors on unseen out-of-sample data (same filter)
7. **Visualizes** final survivors in a professional dark-theme dashboard

## Dashboard Preview

The dashboard shows:
- **Stats bar** - combos tested, IS survivors, final survivors, best return, lowest drawdown
- **Strategy selector** - multi-select dropdown to compare strategies
- **Equity curves** - side-by-side OOS and IS charts with drawdown overlay
- **Results table** - sortable, color-coded with all metrics (return, drawdown, Sharpe, Sortino, win rate, trades)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the engine
python main.py
```

The dashboard auto-opens at `http://127.0.0.1:8050`

## Architecture

```
├── config.py              # Configuration & parameter grids
├── data_fetcher.py        # Binance API + CSV caching
├── indicators/            # Modular indicators (auto-discovered)
│   ├── rsi.py             # RSI (periods: 10, 14, 21)
│   ├── sma_cross.py       # SMA crossover (4 period pairs)
│   ├── ema.py             # EMA crossover (5 period pairs)
│   ├── macd.py            # MACD (standard 12/26/9)
│   └── bollinger.py       # Bollinger Bands (3 variants)
├── rules/                 # Modular trading rules (auto-discovered)
│   ├── rsi_oversold.py    # RSI oversold/overbought (9 variants)
│   ├── sma_cross_rule.py  # SMA golden/death cross (4 variants)
│   ├── ema_cross_rule.py  # EMA crossover (5 variants)
│   ├── macd_cross_rule.py # MACD signal crossover (1 variant)
│   └── bollinger_rule.py  # Bollinger band touch (3 variants)
├── engine.py              # vectorbt backtest engine
├── pipeline.py            # Full pipeline (parallel execution)
├── dashboard.py           # Plotly Dash dashboard
└── main.py                # Entry point
```

## Parameter Sweep

The engine tests **22 individual strategy variants** from 5 indicator types, then generates **all 2-rule combinations** (253 total combos by default). Parameter grids are configured in `config.py`:

| Indicator | Parameters | Variants |
|-----------|-----------|----------|
| RSI | periods [10, 14, 21] x thresholds [(20,80), (25,75), (30,70)] | 9 |
| SMA Cross | period pairs [(10,30), (20,50), (20,100), (50,200)] | 4 |
| EMA Cross | period pairs [(5,13), (9,21), (9,50), (12,26), (20,50)] | 5 |
| MACD | standard (12, 26, 9) | 1 |
| Bollinger | (window, std) [(20,2.0), (20,1.5), (30,2.0)] | 3 |

## Adding Custom Indicators & Rules

### New Indicator

Create `indicators/my_indicator.py`:

```python
from indicators import register
from indicators.base import BaseIndicator

@register
class MyIndicator(BaseIndicator):
    def __init__(self, period=14):
        self.period = period

    @property
    def name(self):
        return f"my_ind_{self.period}"

    def compute(self, df):
        df[f"my_col_{self.period}"] = df["close"].rolling(self.period).mean()
        return df

    @classmethod
    def get_variants(cls):
        return [cls(period=p) for p in [10, 14, 21]]
```

### New Rule

Create `rules/my_rule.py`:

```python
from rules import register
from rules.base import BaseRule

@register
class MyRule(BaseRule):
    def __init__(self, period=14, threshold=50):
        self.period = period
        self.threshold = threshold

    @property
    def name(self):
        return f"My Rule({self.period}, {self.threshold})"

    @property
    def required_indicators(self):
        return [f"my_ind_{self.period}"]

    def generate_signals(self, df):
        col = f"my_col_{self.period}"
        entries = (df["close"] > df[col]).fillna(False)
        exits = (df["close"] < df[col]).fillna(False)
        return entries, exits

    @classmethod
    def get_variants(cls):
        return [cls(period=p, threshold=t) for p in [10, 14] for t in [40, 50]]
```

Drop the file in, run `python main.py` - the engine auto-discovers it.

## Configuration

Edit `config.py` to change:

```python
SYMBOL = "BTCUSDT"           # Any Binance trading pair
TIMEFRAME = "1h"             # 1m, 5m, 15m, 1h, 4h, 1d
LOOKBACK_DAYS = 365          # Historical data period
TRAIN_RATIO = 0.6            # 60% in-sample, 40% out-of-sample
MAX_DRAWDOWN_THRESHOLD = 0.30  # 30% max drawdown = fail
COMBO_MAX_SIZE = 2           # Max rules per combo (1=singles, 2=pairs)
INITIAL_CAPITAL = 10000      # Starting portfolio value
PARALLEL_WORKERS = 8         # Concurrent backtest threads
```

## Pipeline Flow

```
Binance API → CSV Cache → 60/40 Split
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
        In-Sample (60%)                Out-of-Sample (40%)
              │                               │
    ┌─────────┴─────────┐                     │
    ▼                   ▼                     │
  Compute           Generate                  │
  Indicators        Signals                   │
    │                   │                     │
    └────────┬──────────┘                     │
             ▼                                │
      vectorbt Backtest                       │
      (parallel, 8 workers)                   │
             │                                │
             ▼                                │
      Max DD < 30%? ──FAIL──→ eliminated      │
             │                                │
           PASS (survivors)                   │
             │                                │
             └────────────────────────────────┘
                              │
                    Same pipeline on OOS data
                              │
                        Max DD < 30%?
                         │         │
                       PASS      FAIL
                         │         │
                    Dashboard   Eliminated
```

## Tech Stack

- **vectorbt** - High-performance backtesting engine
- **pandas / numpy** - Data manipulation
- **ta** - Technical analysis indicator library
- **Plotly Dash** - Interactive dashboard
- **Binance REST API** - Free market data (no API key needed)

## License

MIT
