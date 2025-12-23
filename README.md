# Multi-Strategy Backtester with AIMD

A production-ready, modular backtesting framework that supports multiple trading strategies with AIMD (Additive Increase Multiplicative Decrease) position sizing and beautiful visualizations.

## Quick Start

Simply run:
```bash
python main.py
```

This will:
- ✅ Load all strategies from config
- ✅ Process all days in the specified range
- ✅ Save trade sheets to `./trade_sheets/`
- ✅ Generate beautiful day-wise price charts with signals in `./results/plots/daily/`
- ✅ Create PnL curves and fine-grained equity curves in `./results/plots/`
- ✅ Save portfolio snapshots for detailed equity tracking in `./results/portfolio_snapshots.csv`
- ✅ Save comprehensive results to `./results/`

## Features

### 🎯 Multi-Strategy Support
- Run multiple strategies simultaneously
- Each strategy has its own TP/SL parameters
- AIMD position sizing adapts based on performance
- Share cap to limit total exposure

### 📊 Beautiful Visualizations
- **Day-wise Price Charts**: Price action with entry/exit signals and position sizes
- **PnL Bar Chart**: Daily profit/loss across all days
- **Fine-Grained Equity Curve**: High-resolution equity tracking using portfolio snapshots (configurable interval)
- **Portfolio Snapshots**: Periodic snapshots of equity, cash, and inventory throughout trading
- All plots are saved automatically with high resolution

### 🔧 Fully Configurable
- Data directory and file ranges in config
- Strategy selection and parameters in config
- AIMD parameters (share cap, rewards, penalties)
- Transaction costs and trade execution rules

### 📈 Comprehensive Results
- Day-wise trade sheets with full details
- Combined trade book across all days
- Performance statistics (win rate, max drawdown, etc.)
- Strategy-level performance breakdown

## Architecture

### Core Components

```
Multi_Strat_Backtester/
├── AIMD.py              # Position and Asks management
├── engine.py            # Orchestrator class (main backtest engine)
├── strategy.py          # Base Strategy class + example strategies
├── main.py              # Entry point - run this!
├── utils.py             # Utility functions
├── visualizations.py    # Beautiful plotting functions
├── config.yaml          # Configuration file
├── data/                # Market data directory
├── results/             # Output directory
│   ├── plots/
│   │   ├── daily/       # Day-wise price charts
│   │   └── pnl_and_equity_curve.png
│   ├── all_trades.csv
│   ├── portfolio_snapshots.csv
│   └── day_wise_summary.csv
└── trade_sheets/        # Individual day trade sheets
```

### Key Classes

#### **Orchestrator** (engine.py)
The main backtesting engine that:
- Processes market data tick by tick
- Manages multiple strategies with AIMD position sizing
- Executes simulated trades with TP/SL management
- Tracks PnL and maintains detailed trade logs
- Handles EOD square-offs

#### **Position** (AIMD.py)
Manages positions across strategies:
- Normalizes positions to respect share cap
- Tracks buffer for overflow positions
- Handles position updates based on signals

#### **Asks** (AIMD.py)
Manages ask sizes using AIMD:
- Additive Increase on profitable trades
- Multiplicative Decrease on losing trades

#### **Strategy** (strategy.py)
Base class for all strategies:
- `update_indicators()`: Process new tick data
- `check_long_entry()`: Entry logic for longs
- `check_short_entry()`: Entry logic for shorts
- `check_long_exit()`: Exit logic for longs
- `check_short_exit()`: Exit logic for shorts

## Configuration

Edit `config.yaml` to customize everything:

```yaml
backtester:
  tran_cost: 0.0002  # Transaction cost (0.02%)
  strategies:
    - name: "Strategy_A"
      position_size: 10
      tp: 0.004   # Take profit (0.4%)
      sl: 0.1     # Stop loss (10%)
    - name: "Strategy_B"
      position_size: 15
      tp: 0.006   # Take profit (0.6%)
      sl: 0.08    # Stop loss (8%)
    - name: "Strategy_C"
      position_size: 20
      tp: 0.005   # Take profit (0.5%)
      sl: 0.12    # Stop loss (12%)
  share_cap: 100        # Max total position across all strategies
  initial_ask: 10       # Initial ask size per strategy
  reward_add: 33        # Additive increase on profit
  penalty_mult: 0.666   # Multiplicative decrease on loss
  save_day_wise_tradesheets: true

data:
  directory: "path-to-your-data"  # Directory with day CSV files
  file_range:
    - [51, 123]          # Process days 51-122
```

## Data Format

CSV files must have two columns:
- **Time**: HH:MM:SS format (e.g., 09:15:00)
- **Price**: Market price at that time
- All other data a strategy will need to execute trades

Example:
```csv
Time,Price
09:15:00,100.50
09:15:01,100.52
09:15:02,100.48
```

## Output Files

### Trade Sheets (`./trade_sheets/`)
Individual CSV files per day with columns:
- Time, Tick, Price, Strategy, Action
- Quantity, Position, PnL, CumulativePnL
- TransactionCost, HoldingDuration

### Day-wise Summary (`./results/day_wise_summary.csv`)
Summary statistics per day:
- Day, Total_PnL, Total_Fees, Trade_Count, Final_Positions

### Combined Trades (`./results/all_trades.csv`)
All trades across all days combined

### Portfolio Snapshots (`./results/portfolio_snapshots.csv`)
Periodic snapshots of portfolio state:
- Time, Day, Equity, Cash, Inventory
- Used for fine-grained equity curve visualization

### Visualizations (`./results/plots/`)
- `daily/day{N}_price_signals.png`: Price chart with signals
- `pnl_and_equity_curve.png`: Daily PnL bars and fine-grained equity curve

## Performance Metrics

The system automatically calculates:
- ✅ Total PnL
- ✅ Total Fees
- ✅ Total Trades
- ✅ Average Daily PnL
- ✅ Win Rate
- ✅ Best/Worst Days
- ✅ Maximum Drawdown (from fine-grained equity curve)
- ✅ Fine-grained equity tracking via portfolio snapshots

## Risk Management

### Built-in Features
- **Take Profit**: Strategy-specific TP levels
- **Stop Loss**: Strategy-specific SL levels
- **Share Cap**: Maximum total position across strategies
- **EOD Square-off**: All positions closed at end of day
- **Minimum Trade Interval**: 5 seconds between trades
- **Transaction Costs**: Realistic cost modeling

### AIMD Position Sizing
- Increases position size on winning trades (Additive)
- Decreases position size on losing trades (Multiplicative)
- Adapts to strategy performance in real-time

## Dependencies

```bash
pip install pandas numpy matplotlib pyyaml easydict
```

