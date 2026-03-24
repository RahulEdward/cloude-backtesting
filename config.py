"""
Configuration for the trading engine.
All tunable parameters live here.
"""

# ── Market Type ──
# "crypto"  → Binance API (e.g. BTCUSDT, ETHUSDT)
# "stock"   → Yahoo Finance (e.g. RELIANCE.NS, TCS.NS, AAPL, MSFT)
# "forex"   → Yahoo Finance (e.g. EURUSD=X, GBPUSD=X, USDINR=X)
MARKET = "stock"

# ── Data Settings ──
SYMBOL = "RELIANCE.NS"
TIMEFRAME = "1h"           # Binance: 1m,5m,15m,1h,4h,1d | Yahoo: 1m,5m,15m,1h,1d,1wk
LOOKBACK_DAYS = 365        # How far back to fetch

# ── CSV Cache ──
CSV_CACHE_DIR = "data_cache"  # Downloaded data saved here to avoid re-fetching

# ── Train/Test Split ──
TRAIN_RATIO = 0.6          # 60% in-sample, 40% out-of-sample

# ── Backtest Settings ──
INITIAL_CAPITAL = 10000.0
FEES = 0.0003              # 0.1% crypto | 0.0003 Indian stocks | 0.00002 forex
SLIPPAGE = 0.0             # No slippage modeled by default

# ── Pass/Fail Threshold ──
MAX_DRAWDOWN_THRESHOLD = 0.30  # Strategies with max drawdown > 30% FAIL

# ── Combo Settings ──
COMBO_MAX_SIZE = 2          # 1 = singles only, 2 = also test pairs, etc.

# ── Parallel Execution ──
PARALLEL_WORKERS = 8        # ThreadPoolExecutor workers for backtesting

# ── Parameter Grids (sweep these to generate strategy variants) ──
RSI_PERIODS = [10, 14, 21]
RSI_THRESHOLDS = [(20, 80), (25, 75), (30, 70)]

SMA_PERIODS = [(10, 30), (20, 50), (20, 100), (50, 200)]

EMA_PERIODS = [(5, 13), (9, 21), (9, 50), (12, 26), (20, 50)]

MACD_PARAMS = [(12, 26, 9)]  # (fast, slow, signal) - standard only

BOLLINGER_PARAMS = [(20, 2.0), (20, 1.5), (30, 2.0)]  # (window, num_std)

# ── Logging ──
LOG_DIR = "logs"
LOG_FILE = "logs/engine.log"
LOG_LEVEL_CONSOLE = "INFO"
LOG_LEVEL_FILE = "DEBUG"

# ── Dashboard ──
DASHBOARD_PORT = 8050
DASHBOARD_HOST = "127.0.0.1"
