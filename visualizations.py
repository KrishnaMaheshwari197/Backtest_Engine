"""
Visualization functions for backtesting results.
Creates beautiful plots for PnL, equity curves, and price charts with signals.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
from datetime import datetime
import numpy as np


def setup_plot_style():
    """Set up consistent plot styling."""
    plt.style.use('seaborn-v0_8-darkgrid')
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.facecolor'] = '#f8f9fa'
    plt.rcParams['grid.alpha'] = 0.3
    plt.rcParams['font.size'] = 10


def plot_price_with_signals(day_num: int, trade_df: pd.DataFrame, data_df: pd.DataFrame, 
                            output_dir: str = "results/plots/daily") -> None:
    """
    Plot price chart with buy/sell signals and position sizes.
    
    Args:
        day_num: Day number for the plot title
        trade_df: DataFrame with trades (columns: Time, Price, Action, Quantity, Strategy, Position)
        data_df: DataFrame with market data (columns: Time, Price)
        output_dir: Directory to save the plot
    """
    setup_plot_style()
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Convert time to datetime for plotting (make copies to avoid SettingWithCopyWarning)
    fixed_date = pd.to_datetime("2025-01-01")
    
    data_df = data_df.copy()
    trade_df = trade_df.copy()
    
    if isinstance(data_df['Time'].iloc[0], str):
        data_df['Time'] = pd.to_datetime(data_df['Time'], format='%H:%M:%S').dt.time
    
    data_df['datetime'] = data_df['Time'].apply(lambda t: pd.Timestamp.combine(fixed_date, t))
    trade_df['datetime'] = trade_df['Time'].apply(lambda t: pd.Timestamp.combine(fixed_date, t))
    
    # Create figure with better size
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), height_ratios=[3, 1])
    fig.suptitle(f'Day {day_num} - Price Action & Trading Signals', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    # Plot 1: Price with signals
    ax1.plot(data_df['datetime'], data_df['Price'], 
             label='Price', color='#2E86AB', linewidth=1.5, alpha=0.8)
    ax1.set_ylabel('Price', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3, linestyle='--')
    
    # Handle empty trade_df
    if len(trade_df) == 0:
        ax1.text(0.5, 0.5, 'No Trades', transform=ax1.transAxes,
                ha='center', va='center', fontsize=16, alpha=0.5)
    
    # Separate buy and sell trades
    buys = trade_df[trade_df['Side'] == 'Buy'] if len(trade_df) > 0 else pd.DataFrame()
    sells = trade_df[trade_df['Side'] == 'Sell'] if len(trade_df) > 0 else pd.DataFrame()
    
    # Plot buy signals
    for _, trade in buys.iterrows():
        color = '#06D6A0'
        marker = '^'
        
        ax1.scatter(trade['datetime'], trade['Price'], 
                   color=color, marker=marker, s=200, 
                   edgecolors='white', linewidths=2, zorder=5, alpha=0.9)
        
        # Add position size annotation
        ax1.annotate(f"{abs(trade['Quantity']):.0f}", 
                    xy=(trade['datetime'], trade['Price']),
                    xytext=(0, -25),
                    textcoords='offset points',
                    ha='center',
                    fontsize=9,
                    fontweight='bold',
                    color=color,
                    bbox=dict(boxstyle='round,pad=0.4', 
                            facecolor='white', 
                            edgecolor=color, 
                            linewidth=2, 
                            alpha=0.9))
    
    # Plot sell signals
    for _, trade in sells.iterrows():
        color = '#EF476F'
        marker = 'v'
        
        ax1.scatter(trade['datetime'], trade['Price'], 
                   color=color, marker=marker, s=200, 
                   edgecolors='white', linewidths=2, zorder=5, alpha=0.9)
        
        # Add position size annotation
        ax1.annotate(f"{abs(trade['Quantity']):.0f}", 
                    xy=(trade['datetime'], trade['Price']),
                    xytext=(0, 25),
                    textcoords='offset points',
                    ha='center',
                    fontsize=9,
                    fontweight='bold',
                    color=color,
                    bbox=dict(boxstyle='round,pad=0.4', 
                            facecolor='white', 
                            edgecolor=color, 
                            linewidth=2, 
                            alpha=0.9))
    
    # Legend
    buy_marker = mpatches.Patch(color='#06D6A0', label='Buy ▲')
    sell_marker = mpatches.Patch(color='#EF476F', label='Sell ▼')
    ax1.legend(handles=[buy_marker, sell_marker], 
              loc='upper left', framealpha=0.9, fontsize=10)
    
    # Plot 2: Inventory over time
    if len(trade_df) > 0:
        # Aggregate inventory across trades
        position_timeline = []
        for _, trade in trade_df.iterrows():
            position_timeline.append({
                'datetime': trade['datetime'],
                'position': trade['Inventory']
            })
        
        if position_timeline:
            pos_df = pd.DataFrame(position_timeline)
            ax2.fill_between(pos_df['datetime'], 0, pos_df['position'], 
                            where=(pos_df['position'] >= 0), 
                            color='#06D6A0', alpha=0.4, label='Long Position')
            ax2.fill_between(pos_df['datetime'], 0, pos_df['position'], 
                            where=(pos_df['position'] < 0), 
                            color='#EF476F', alpha=0.4, label='Short Position')
            ax2.plot(pos_df['datetime'], pos_df['position'], 
                    color='#2E86AB', linewidth=2, alpha=0.8)
            ax2.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
            ax2.set_ylabel('Position Size', fontsize=12, fontweight='bold')
            ax2.set_xlabel('Time', fontsize=12, fontweight='bold')
            ax2.grid(True, alpha=0.3, linestyle='--')
            ax2.legend(loc='upper left', framealpha=0.9, fontsize=10)
    
    # Format x-axis
    for ax in [ax1, ax2]:
        ax.tick_params(axis='x', rotation=45)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    
    # Save plot
    output_path = Path(output_dir) / f"day{day_num}_price_signals.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  ✓ Price chart saved: {output_path}")


def plot_pnl_curve(day_results: pd.DataFrame, snap_book: pd.DataFrame = None, output_dir: str = "results/plots") -> None:
    """
    Plot daily PnL curve across all days and fine-grained equity curve from snapshots.
    
    Args:
        day_results: DataFrame with columns [Day, Total_PnL, Total_Fees, Trade_Count]
        snap_book: DataFrame with snapshot data [Time, Day, Equity, Cash, Inventory]
        output_dir: Directory to save the plot
    """
    setup_plot_style()
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle('Performance Analysis', fontsize=16, fontweight='bold')
    
    # Plot 1: Daily PnL
    colors = ['#06D6A0' if x >= 0 else '#EF476F' for x in day_results['Total_PnL']]
    bars = ax1.bar(day_results['Day'], day_results['Total_PnL'], 
                   color=colors, alpha=0.7, edgecolor='white', linewidth=1)
    
    # Add value labels on bars
    for i, (bar, value) in enumerate(zip(bars, day_results['Total_PnL'])):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{value:.1f}',
                ha='center', va='bottom' if height >= 0 else 'top',
                fontsize=8, fontweight='bold')
    
    ax1.axhline(y=0, color='gray', linestyle='-', linewidth=1, alpha=0.5)
    ax1.set_ylabel('Daily PnL', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Day', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y', linestyle='--')
    ax1.set_title('Daily Profit & Loss', fontsize=13, fontweight='bold', pad=10)
    
    # Plot 2: Cumulative PnL (Equity Curve) from snapshots
    if snap_book is not None and len(snap_book) > 0:
        # Use fine-grained equity data from snapshots
        initial_equity = snap_book['Equity'].iloc[0]
        snap_book['Cumulative_PnL'] = snap_book['Equity'] - initial_equity
        
        # Create x-axis as continuous time across days
        snap_book['TimeIndex'] = range(len(snap_book))
        
        ax2.plot(snap_book['TimeIndex'], snap_book['Cumulative_PnL'], 
                color='#2E86AB', linewidth=1.5, alpha=0.8)
        ax2.fill_between(snap_book['TimeIndex'], 0, snap_book['Cumulative_PnL'], 
                         where=(snap_book['Cumulative_PnL'] >= 0), 
                         color='#06D6A0', alpha=0.2)
        ax2.fill_between(snap_book['TimeIndex'], 0, snap_book['Cumulative_PnL'], 
                         where=(snap_book['Cumulative_PnL'] < 0), 
                         color='#EF476F', alpha=0.2)
        
        # Mark day boundaries
        day_changes = snap_book[snap_book['Day'] != snap_book['Day'].shift()].index
        for idx in day_changes[1:]:  # Skip first day
            ax2.axvline(x=idx, color='gray', linestyle='--', linewidth=0.5, alpha=0.3)
        
        cumulative_pnl_final = snap_book['Cumulative_PnL'].iloc[-1]
        max_dd = (snap_book['Cumulative_PnL'] - snap_book['Cumulative_PnL'].cummax()).min()
    else:
        # Fallback to day-level cumulative PnL
        cumulative_pnl = day_results['Total_PnL'].cumsum()
        ax2.plot(day_results['Day'], cumulative_pnl, 
                color='#2E86AB', linewidth=2.5, marker='o', 
                markersize=6, markerfacecolor='white', markeredgewidth=2)
        ax2.fill_between(day_results['Day'], 0, cumulative_pnl, 
                         where=(cumulative_pnl >= 0), 
                         color='#06D6A0', alpha=0.2)
        ax2.fill_between(day_results['Day'], 0, cumulative_pnl, 
                         where=(cumulative_pnl < 0), 
                         color='#EF476F', alpha=0.2)
        cumulative_pnl_final = cumulative_pnl.iloc[-1]
        max_dd = (cumulative_pnl - cumulative_pnl.cummax()).min()
    
    ax2.axhline(y=0, color='gray', linestyle='-', linewidth=1, alpha=0.5)
    ax2.set_ylabel('Cumulative PnL', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Time (Snapshots)' if snap_book is not None and len(snap_book) > 0 else 'Day', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.set_title('Equity Curve (Fine-Grained)', fontsize=13, fontweight='bold', pad=10)
    
    # Add statistics box
    total_pnl = cumulative_pnl_final
    avg_pnl = day_results['Total_PnL'].mean()
    win_rate = (day_results['Total_PnL'] > 0).sum() / len(day_results) * 100
    
    stats_text = f'Total PnL: {total_pnl:.2f}\n'
    stats_text += f'Avg Daily PnL: {avg_pnl:.2f}\n'
    stats_text += f'Win Rate: {win_rate:.1f}%\n'
    stats_text += f'Max Drawdown: {max_dd:.2f}'
    
    ax2.text(0.02, 0.98, stats_text,
            transform=ax2.transAxes,
            fontsize=10,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='white', 
                     edgecolor='#2E86AB', linewidth=2, alpha=0.9))
    
    plt.tight_layout()
    
    output_path = Path(output_dir) / "pnl_and_equity_curve.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"\n✓ PnL & Equity curve saved: {output_path}")



