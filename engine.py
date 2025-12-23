import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import time
from easydict import EasyDict

from aimd import Position, Asks
from strategy import Strategy
from utils import time_to_seconds, seconds_to_time


class Orchestrator:
    def __init__(self, strategies: List[Strategy], config: EasyDict):

        self.strategies = strategies
        self.num_strats = len(strategies)
        self.config = config
        
        # Engine components
        inventory_limit = config.engine.get('inventory_limit', 100)
        self.trade_limit = config.engine.get('trade_limit', 100)
        self.position = Position(num_strats=self.num_strats, inventory_limit=inventory_limit, trade_limit=self.trade_limit)
        self.cooldown_period = config.engine.get('cooldown_period', 15)  # in ticks  
        self.cash = config.engine.get('initial_equity', 100000)
        self.initial_equity = self.cash
        self.equity = self.cash
        self.current_asks = Asks(
            num_strats=self.num_strats,
            initial_ask=config.engine.aimd.get('initial_ask', 10),
            reward_add=config.engine.aimd.get('reward_add', 33),
            penalty_mult=config.engine.aimd.get('penalty_mult', 0.666)
        )
        self.snapshot_period = config.engine.get('snapshot_period', 300)  # in seconds


        # Trading parameters
        self.tran_cost = config.engine.transaction_cost
        
        # Store strategy-specific TP/SL values and names from config (absolute values)
        self.tp_list = [strat_config.tp for strat_config in config.strategies]
        self.sl_list = [strat_config.sl for strat_config in config.strategies]
        self.strategy_names = [strat_config.name for strat_config in config.strategies]

        # State tracking
        self.entry_prices = [0.0] * self.num_strats
        self.entry_times = [None] * self.num_strats
        self.signals = [0] * self.num_strats
        # self.tp_sl_hit = [False] * self.num_strats  # Track which strategies hit TP/SL for logging
        self.last_trade_time = -self.cooldown_period
        self.day_length = 6 * 3600  # 6 hours 10 minutes in seconds
        self.eod_squared_off = False  # Flag to block trades after EOD
        self.current_pointer = 0  # Current time pointer in seconds
        self.trade_backlog = 0
        self.current_inventory = 0


        # Day tracking
        self.current_day = None
        self.day_start_equity = 0.0
        self.day_start_fees = 0.0
        self.day_start_trades = 0
        self.day_start_trade_idx = 0
        
        # Performance tracking
        self.total_fee = 0.0
        
        # Trade book
        self.trade_book = pd.DataFrame(columns=[
            "Time", "Price", "Quantity", "Side", 
            "Inventory", "Transaction Cost", "Day"
        ])
        self.snap_book = pd.DataFrame(columns=[
            "Time", "Day", "Equity", "Cash", "Inventory"
        ])

    def process_tick(self, tick_data: Dict, day_num: int) -> None:

        if self.current_day != day_num:
            # New day initialization
            self.current_day = day_num
            # Update equity with first tick price of new day
            self.equity = self.cash + self.current_inventory * tick_data['Price']
            self.last_trade_time = -self.cooldown_period
            self.day_start_equity = self.equity
            self.day_start_fees = self.total_fee
            self.day_start_trade_idx = len(self.trade_book)
            self.eod_squared_off = False
        self.current_pointer = time_to_seconds(tick_data['Time'])
        
        if not self.eod_squared_off:
            for i, strategy in enumerate(self.strategies):
                strategy.update_indicators(tick_data)
        
        if self.current_pointer % self.snapshot_period == 0: 
            self._portfolio_snapshot(tick_data)

        if self.trade_backlog != 0 and self.current_pointer - self.last_trade_time > self.cooldown_period:
            self.execute_trade(tick_data)
            return 

        if self.eod_squared_off:
            return
        
        if self.current_pointer >= self.day_length:
            prev_pos = self.position.pos.copy()
            self.position.reset_position()
            self.trade_backlog += -sum(prev_pos)
            self.eod_squared_off = True
            for i, strategy in enumerate(self.strategies):
                strategy.reset()
            return
        
        signals = self.get_signals(tick_data)
        
        prev_pos = self.position.pos.copy() 
        trades_to_execute, aimd = self.position.update_position(signals, self.current_asks.asks)
        self.trade_backlog += trades_to_execute
        curr_pos = self.position.pos.copy()
        current_price = tick_data['Price']
        for i, strategy in enumerate(self.strategies):
            # Update strategy position and pass entry price when entering
            if prev_pos[i] == 0 and curr_pos[i] != 0:
                # Entering new position - pass entry price
                strategy.update_position(curr_pos[i], current_price)
                self.entry_prices[i] = current_price
                self.entry_times[i] = tick_data['Time']
            elif curr_pos[i] == 0 and prev_pos[i] != 0:
                # Exiting position - reset entry price
                strategy.update_position(0, 0.0)
                self.entry_prices[i] = 0.0
                self.entry_times[i] = None
            # No position change, no update needed
        pnl_list = self._compute_strategy_pnl( current_price=tick_data['Price'], prev_pos=prev_pos, final_pos=curr_pos)
        self.current_asks.update(pnl_list, aimd)


        
    

    def get_signals(self, tick_data: Dict):
        signals = [0] * self.num_strats
        pos = self.position.pos.copy()
        for i, strategy in enumerate(self.strategies):
            if pos[i] == 0: 
                if strategy.check_long_entry():
                    signals[i] = 1
                elif strategy.check_short_entry():
                    signals[i] = -1
            elif pos[i] > 0 and strategy.check_long_exit():
                signals[i] = -1
            elif pos[i] < 0 and strategy.check_short_exit():
                signals[i] = 1
            else: 
                signals[i] = 0  
        return signals

            
    def execute_trade(self, tick_data: Dict) -> None:
            execute_qty = min(abs(self.trade_backlog), self.trade_limit)*np.sign(self.trade_backlog)
            self.trade_backlog -= execute_qty
            self.current_inventory += execute_qty
            self.cash -= (execute_qty * tick_data['Price'] + self.tran_cost * tick_data['Price'] * abs(execute_qty))
            self.total_fee += self.tran_cost * tick_data['Price'] * abs(execute_qty)
            if self.config.engine.get('verbose_snapshots', False):
                print(f"\n  !! Executed trade: {'Buy' if execute_qty > 0 else 'Sell'} {abs(execute_qty)} at {tick_data['Price']} at {tick_data['Time']}")
            self._log_order(
                time=tick_data['Time'],
                price=tick_data['Price'],
                quantity=abs(execute_qty),
                side="Buy" if execute_qty > 0 else "Sell"
            )
            self.last_trade_time = self.current_pointer

    def _compute_strategy_pnl(self, current_price: float, prev_pos: List[float], 
                              final_pos: List[float]) -> List[float]:
        """
        Compute PnL for each strategy.
        
        Args:
            current_price: Current market price
            prev_pos: Previous position array
            final_pos: Final position array after trade
            
        Returns:
            List of PnL values for each strategy
        """
        pnl_list = [0.0] * self.num_strats
        
        for i in range(self.num_strats):
            # Calculate PnL only if position was closed (reduced or flipped)
            if prev_pos[i] != 0 and final_pos[i] * prev_pos[i] <= 0:
                pnl = self._calc_pnl(self.entry_prices[i], current_price, prev_pos[i])
                pnl_list[i] = pnl
        
        return pnl_list
    
    def _calc_pnl(self, entry_price: float, exit_price: float, position: float) -> float:
        price_pnl = (exit_price - entry_price) * np.sign(position)
        
        # Transaction costs (entry + exit)
        transaction_cost = self.tran_cost * (entry_price + exit_price)
        
        # Total PnL for the position
        pnl = (price_pnl - transaction_cost) * abs(position)
        self.total_fee += transaction_cost * abs(position)
        
        return pnl
    
    def _calc_holding_duration(self, exit_time: time, entry_time: time) -> str:
        if entry_time is None:
            return "00:00:00"
        duration_seconds = abs(time_to_seconds(exit_time) - time_to_seconds(entry_time))
        return seconds_to_time(duration_seconds)
    
    def _log_order(self, time: time, price: float,
                   quantity: int, side: str) -> None:
        """
        Log a trade to the trade book.
        
        Args:
            time: Trade time
            price: Trade price
            quantity: Trade quantity (positive for buy, negative for sell)
            position_after: Position after trade
            pnl: Trade PnL
            holding_duration: Holding duration in HH:MM:SS format
        """
        transaction_cost = self.tran_cost * price * abs(quantity)
        
        self.trade_book.loc[len(self.trade_book)] = {
            "Time": time,
            "Price": round(price, 3),
            "Quantity": quantity, 
            "Side": side,
            "Inventory": sum(self.position.pos),
            "Transaction Cost": round(transaction_cost, 4),
            "Day": self.current_day
        }
    def _portfolio_snapshot(self, tick_data) -> None:
        """
        Log current portfolio snapshot (positions and liquid equity).
        """
        self.equity = self.cash + self.current_inventory * tick_data['Price']
        snapshot = {
            "Time": tick_data['Time'],
            "Price": round(tick_data['Price'], 3),
            "Day": self.current_day,
            "Equity": round(self.equity, 2),
            "Cash": round(self.cash, 2),
            "Inventory": sum(self.position.pos)
        }
        if self.config.engine.get('verbose_snapshots', False):
            print(f"\n  > Snapshot at {tick_data['Time']} - Equity: {self.equity:.2f}, Cash: {self.cash:.2f}, Inventory: {self.position.pos}, price: {round(tick_data['Price'], 3)}")
        self.snap_book.loc[len(self.snap_book)] = snapshot    

    def get_day_results(self) -> Dict:
        """
        Get current day's results.
        
        Returns:
            Dictionary with day-specific metrics
        """
        day_trades = self.trade_book[self.day_start_trade_idx:]
        return {
            "trade_book": day_trades,
            "day_pnl": self.equity - self.day_start_equity,
            "day_fees": self.total_fee - self.day_start_fees,
            "day_trade_count": len(day_trades)
        }
    
    def get_results(self) -> Dict:
        """
        Get overall backtesting results.
        
        Returns:
            Dictionary with trade book and performance metrics
        """
        return {
            "trade_book": self.trade_book,
            "snap_book": self.snap_book,
            "total_pnl": self.equity - self.initial_equity,
            "total_fees": self.total_fee,
            "final_positions": self.position.pos,
            "asks": self.current_asks,
            "trade_count": len(self.trade_book)
        }
