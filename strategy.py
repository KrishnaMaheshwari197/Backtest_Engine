"""
Base Strategy Interface and Production Strategies

This module defines the base Strategy class and contains production-ready trading strategies.
Each strategy implements entry/exit logic and indicator updates for tick-by-tick backtesting.
"""

from typing import Dict
from collections import deque
import numpy as np


class Strategy:
    """
    Base class for all trading strategies.
    
    All custom strategies must inherit from this class and implement:
    - update_indicators: Update strategy indicators with new tick data
    - check_long_entry: Determine if conditions are met for long entry
    - check_short_entry: Determine if conditions are met for short entry
    - check_long_exit: Determine if conditions are met to exit long position (includes TP/SL)
    - check_short_exit: Determine if conditions are met to exit short position (includes TP/SL)
    """
    
    def __init__(self, tp: float = 0.0, sl: float = 0.0):
        self.tp = tp  # Take profit threshold (absolute price difference)
        self.sl = sl  # Stop loss threshold (absolute price difference)
        self.entry_price = 0.0  # Entry price for TP/SL calculation
        self.current_tick = {}  # Store current tick data

    def reset(self):
        self.entry_price = 0.0
    
    def update_indicators(self, tick_data: Dict) -> None:
        # Store current tick data for use in check functions
        self.current_tick = tick_data

    def update_position(self, position: int, entry_price: float = 0.0) -> None:
        # Called when position changes - store entry price for TP/SL
        if position != 0:
            self.entry_price = entry_price
        else:
            self.entry_price = 0.0
    
    def check_long_entry(self) -> bool:
        return False
    
    def check_short_entry(self) -> bool:
        return False
    
    def check_long_exit(self) -> bool:
        return False
    
    def check_short_exit(self) -> bool:
        return False



# ============================================================================
# SIMPLE EXAMPLE STRATEGIES (for reference/testing)
# ============================================================================

class Strategy_A(Strategy):
    """
    Dummy Strategy A - Goes long at every hour mark (n*3600).
    Exits via TP/SL only.
    """
    
    def __init__(self, tp: float = 0.0, sl: float = 0.0):
        super().__init__(tp, sl)
        
    def _parse_time_to_seconds(self, time_input) -> int:
        """Convert HH:MM:SS string or datetime.time to seconds"""
        if isinstance(time_input, str):
            parts = time_input.split(":")
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        else:
            return time_input.hour * 3600 + time_input.minute * 60 + time_input.second
        
    def update_indicators(self, tick_data: Dict) -> None:
        super().update_indicators(tick_data)  # Store tick data
    
    def check_long_entry(self) -> bool:
        time_sec = self._parse_time_to_seconds(self.current_tick['Time'])
        # Enter long at every hour mark (0, 3600, 7200, etc.)
        if time_sec % 3600 == 0 and time_sec > 3600:
            return True
        return False
    
    def check_short_entry(self) -> bool:
        return False  # Only goes long
    
    def check_long_exit(self) -> bool:
        # Check TP/SL
        if self.entry_price == 0.0:
            return False
        current_price = self.current_tick['Price']
        pnl = current_price - self.entry_price
        # Exit if TP hit or SL hit
        if pnl >= self.tp or pnl <= -self.sl:
            return True
        return False
    
    def check_short_exit(self) -> bool:
        return False  # Never short


class Strategy_B(Strategy):
    """
    Dummy Strategy B - Goes short at every one and half-hour mark ((2n+0.5)*3600).
    Exits via TP/SL only.
    """
    
    def __init__(self, tp: float = 0.0, sl: float = 0.0):
        super().__init__(tp, sl)
        
    def _parse_time_to_seconds(self, time_input) -> int:
        """Convert HH:MM:SS string or datetime.time to seconds"""
        if isinstance(time_input, str):
            parts = time_input.split(":")
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        else:
            return time_input.hour * 3600 + time_input.minute * 60 + time_input.second
        
    def update_indicators(self, tick_data: Dict) -> None:
        super().update_indicators(tick_data)  # Store tick data
    
    def check_long_entry(self) -> bool:
        return False  # Only goes short
    
    def check_short_entry(self) -> bool:
        time_sec = self._parse_time_to_seconds(self.current_tick['Time'])
        # Enter short at every half-hour mark (1800, 5400, 9000, etc.)
        # Engine checks if position is flat before calling this
        if time_sec % 1800 == 0 and time_sec % 3600 != 0 and self.entry_price == 0.0: 
            return True
        return False
    
    def check_long_exit(self) -> bool:
        return False  # Never long
    
    def check_short_exit(self) -> bool:
        # Check TP/SL
        if self.entry_price == 0.0:
            return False
        current_price = self.current_tick['Price']
        pnl = self.entry_price - current_price  # Reversed for short
        # Exit if TP hit or SL hit
        if pnl >= self.tp or pnl <= -self.sl:
            return True
        return False


class Strategy_C(Strategy):
    """
    Dummy Strategy C - Alternates between long and short every 15 minutes (900 seconds).
    Exits via TP/SL only.
    """
    
    def __init__(self, tp: float = 0.0, sl: float = 0.0):
        super().__init__(tp, sl)
        self.trade_count = 0
        
    def reset(self):
        super().reset()
        self.trade_count = 0
        
    def _parse_time_to_seconds(self, time_input) -> int:
        """Convert HH:MM:SS string or datetime.time to seconds"""
        if isinstance(time_input, str):
            parts = time_input.split(":")
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        else:
            return time_input.hour * 3600 + time_input.minute * 60 + time_input.second
        
    def update_indicators(self, tick_data: Dict) -> None:
        super().update_indicators(tick_data)  # Store tick data
    
    def check_long_entry(self) -> bool:
        time_sec = self._parse_time_to_seconds(self.current_tick['Time'])
        # Enter at every 15-minute mark (0, 900, 1800, 2700, etc.)
        # Engine checks if position is flat before calling this
        if time_sec % 900 == 0:
            # Go long on even intervals (0, 1800, 3600, etc.)
            if self.trade_count % 2 == 0:
                self.trade_count += 1
                return True
        return False
    
    def check_short_entry(self) -> bool:
        time_sec = self._parse_time_to_seconds(self.current_tick['Time'])
        # Enter at every 15-minute mark
        # Engine checks if position is flat before calling this
        if time_sec % 900 == 0:
            # Go short on odd intervals (900, 2700, 4500, etc.)
            if self.trade_count % 2 == 1:
                self.trade_count += 1
                return True
        return False
    
    def check_long_exit(self) -> bool:
        # Check TP/SL
        if self.entry_price == 0.0:
            return False
        current_price = self.current_tick['Price']
        pnl = current_price - self.entry_price
        # Exit if TP hit or SL hit
        if pnl >= self.tp or pnl <= -self.sl:
            return True
        return False
    
    def check_short_exit(self) -> bool:
        # Check TP/SL
        if self.entry_price == 0.0:
            return False
        current_price = self.current_tick['Price']
        pnl = self.entry_price - current_price  # Reversed for short
        # Exit if TP hit or SL hit
        if pnl >= self.tp or pnl <= -self.sl:
            return True
        return False
