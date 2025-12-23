import pandas as pd
from pathlib import Path
import os
import importlib
from datetime import time
from utils import get_cfg
from visualizations import plot_price_with_signals, plot_pnl_curve
from engine import Orchestrator

os.makedirs("./results/plots/daily", exist_ok=True)
os.makedirs("./trade_sheets", exist_ok=True)

def main():
    config = get_cfg()
    strategy_configs = config.strategies
    num_strats = len(strategy_configs)
    print(f"Number of strategies: {num_strats}")
    
    strategy_module = importlib.import_module("strategy")
    
    strategies = []
    for strat_config in strategy_configs:
        strategy_name = strat_config.name
        tp = strat_config.tp
        sl = strat_config.sl
        
        try:
            # Get the strategy class from the module
            StrategyClass = getattr(strategy_module, strategy_name)
            # Instantiate strategy with TP/SL
            strategy_instance = StrategyClass(tp=tp, sl=sl)
            strategies.append(strategy_instance)
            print(f"✓ Loaded {strategy_name} (TP={tp}, SL={sl})")
        except AttributeError:
            print(f"⚠️  Strategy class '{strategy_name}' not found in strategy.py")
            return
    
    if len(strategies) == 0:
        print("⚠️  No strategies loaded. Exiting.")
        return
    
    
    engine = Orchestrator(strategies, config)
    
    print(f"\n✓ Orchestrator initialized with {len(strategies)} strategies")
    print(f"  Inventory limit: {config.engine.get('inventory_limit', 100)}")
    print(f"  Trade limit: {config.engine.get('trade_limit', 100)}")
    print(f"  Initial asks: {engine.current_asks.get_asks()}")
    
    # Print save configuration
    print(f"\n Output Configuration:")
    if config.output.save_trade_sheets:
        print(f"  ✓ Day-wise trade sheets will be saved to: ./trade_sheets/")
    if config.output.plots.save_daily_price_charts:
        print(f"  ✓ Day-wise plots will be saved to: ./results/plots/daily/")
    if config.output.save_combined_trades or config.output.save_day_summary:
        print(f"  ✓ Combined results will be saved to: ./results/")
    
    # Storage for results
    day_results = []
    
    # Get data directory from config
    data_directory = config.data.directory
    print(f"\nData directory: {data_directory}")
    
    # Process each file range
    ranges = config.data.file_range
    
    for start, end in ranges:
        for day_num in range(start, end):
            file_path = Path(data_directory) / f"day{day_num}.csv"
            if not file_path.exists():
                print(f"⚠️  Skipping day {day_num} - file not found")
                continue

            df = pd.read_csv(file_path)
                        
            # Convert Time column to time objects if needed
            if not isinstance(df['Time'].iloc[0], time):
                df['Time'] = pd.to_datetime(df['Time'], format='%H:%M:%S').dt.time
            
            print("\n" + "="*60)
            print(f"Processing Day {day_num}")
            print("="*60)
            print(f"Starting asks: {[int(a) for a in engine.current_asks.get_asks()]}")
            
            # Process each tick for this day
            for idx in range(len(df)):
                tick_data = df.iloc[idx].to_dict()
                engine.process_tick(tick_data, day_num)
            
            # Get day results
            day_result = engine.get_day_results()
            ending_asks = engine.current_asks.get_asks()
            print(f"Ending asks: {[int(a) for a in ending_asks]}")
            print(f"Day PnL: {day_result['day_pnl']:.2f}")
            print(f"Day Trades: {day_result['day_trade_count']}")
            
            # Save day-wise trade sheet if configured
            if config.output.save_trade_sheets and not day_result['trade_book'].empty:
                output_path = f"./trade_sheets/trade_sheet_day{day_num}.csv"
                day_result['trade_book'].to_csv(output_path, index=False)
            
            # Generate day-wise plot if configured
            if config.output.plots.save_daily_price_charts:
                try:
                    plot_price_with_signals(day_num, day_result['trade_book'], df)
                except Exception as e:
                    print(f"  ⚠️  Could not generate plot: {e}")
            
            # Store day summary
            day_summary = {
                'Day': day_num,
                'Total_PnL': day_result['day_pnl'],
                'Total_Fees': day_result['day_fees'],
                'Trade_Count': day_result['day_trade_count']
            }
            day_results.append(day_summary)
    
    # Get final results from orchestrator
    final_results = engine.get_results()
    combined_trades = final_results['trade_book']
    snap_book = final_results['snap_book']
    
    # Save combined trade book if configured
    if config.output.save_combined_trades and not combined_trades.empty:
        combined_trades.to_csv("./results/all_trades.csv", index=False)
        print(f"\n✓ Combined trade book saved to ./results/all_trades.csv")
    elif not combined_trades.empty:
        print(f"\n  Combined trades not saved (disabled in config)")
    else:
        print(f"\n  No trades to save - all days had empty trade books")
    
    # Save snapshot book
    if not snap_book.empty:
        snap_book.to_csv("./results/portfolio_snapshots.csv", index=False)
        print(f"✓ Portfolio snapshots saved to ./results/portfolio_snapshots.csv")
    
    if len(day_results) > 0:
        summary_df = pd.DataFrame(day_results)
        
        # Save day-wise summary if configured
        if config.output.save_day_summary:
            summary_df.to_csv("./results/day_wise_summary.csv", index=False)
            print(f"✓ Day-wise summary saved to ./results/day_wise_summary.csv")
        
        # Generate PnL and equity curve plots if configured
        if config.output.plots.save_pnl_curve:
            try:
                plot_pnl_curve(summary_df, snap_book)
            except Exception as e:
                print(f"⚠️  Could not generate PnL curve: {e}")
        
        # Print overall statistics
        print("\n" + "="*60)
        print("OVERALL STATISTICS")
        print("="*60)
        print(f"Total Days Processed: {len(day_results)}")
        print(f"Total PnL: {final_results['total_pnl']:.2f}")
        print(f"Total Fees: {final_results['total_fees']:.2f}")
        print(f"Total Trades: {final_results['trade_count']}")
        print(f"Average Daily PnL: {summary_df['Total_PnL'].mean():.2f}")
        print(f"Win Rate: {(summary_df['Total_PnL'] > 0).sum() / len(summary_df) * 100:.1f}%")
        print(f"Best Day: {summary_df['Total_PnL'].max():.2f} (Day {summary_df.loc[summary_df['Total_PnL'].idxmax(), 'Day']:.0f})")
        print(f"Worst Day: {summary_df['Total_PnL'].min():.2f} (Day {summary_df.loc[summary_df['Total_PnL'].idxmin(), 'Day']:.0f})")
        print(f"Average PnL per Share: {final_results['total_pnl'] / config.engine.get('inventory_limit', 100):.4f}")
        print(f"Final Asks: {[int(a) for a in final_results['asks'].get_asks()]}")
    else:
        print("\n⚠️  No results to save")


if __name__ == "__main__":
    main()