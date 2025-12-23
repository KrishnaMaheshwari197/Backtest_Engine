from typing import List


class Position:    
    def __init__(self, num_strats: int = 5, inventory_limit: int = 100, trade_limit: int = 100):
        """       
        Args:
            num_strats: Number of strategies to manage
            inventory_limit: Maximum position size available at one time
            trade_limit: Threshold above which shares go to buffer
        """
        self.num_strats = num_strats
        self.inventory_limit = inventory_limit
        self.trade_limit = trade_limit
        self.pos = [0] * num_strats
    
    def normalize(self, pos: List[float]) -> List[float]:
        """
        Args:
            pos: List of position sizes
        Returns:
            Normalized position list
        """
        current_limit = 0
        for i in range(len(pos)):
            if current_limit + abs(pos[i]) > self.inventory_limit:
                pos[i] = (self.inventory_limit - current_limit) * (1 if pos[i] > 0 else -1)
                current_limit = self.inventory_limit
            elif current_limit + abs(pos[i]) <= self.inventory_limit:
                current_limit += abs(pos[i])
        return pos
    
    def update_position(self, signals: List[int], asks_abs: List[float]) -> tuple:
        """
        Args:
            signals: List of signals (+1 long, -1 short, 0 no signal) for each strategy
            asks_abs: List of absolute position sizes requested by each strategy
            
        Returns:
            Tuple of (net_trade_quantity, aimd_flags)
        """
        # Convert absolute asks to signed asks based on signals
        asks = [asks_abs[i] * signals[i] for i in range(len(asks_abs))]
        prev_pos = self.pos.copy()
        pos = self.pos.copy()
        aimd = [0] * len(asks_abs)
        direction = 0
        
        for i in range(len(signals)):
            if asks[i] * pos[i] < 0: ## SQUARE OFF CONDITION
                aimd[i] = 1  
                pos[i] = 0
                asks[i] = 0
            elif direction: 
                if asks[i] * direction > 0 and pos[i] == 0:
                    pos[i] += asks[i]
                    asks[i] = 0
                elif pos[i] * direction <0:
                    aimd[i] = 1
                    pos[i] = 0
            else:
                direction = 1 if asks[i] > 0 else -1 if asks[i] < 0 else 1 if pos[i] > 0 else -1 if pos[i] < 0 else 0
                pos[i] += asks[i]
        self.pos = self.normalize(pos)
        
        # Calculate net trade quantity
        current_exposure = sum(self.pos)
        prev_exposure = sum(prev_pos)
        trades_to_execute = current_exposure - prev_exposure
                
        return trades_to_execute, aimd
    
    def reset_position(self):
        """Reset all positions to zero."""
        self.pos = [0] * self.num_strats


class Asks:
    """
    Manages ask sizes for each strategy using AIMD algorithm.
    Increases ask size on profit (Additive Increase).
    Decreases ask size on loss (Multiplicative Decrease).
    """
    
    def __init__(self, num_strats: int = 5, initial_ask: int = 10, 
                 reward_add: int = 33, penalty_mult: float = 0.666):
        """
        Initialize Asks manager.
        
        Args:
            num_strats: Number of strategies
            initial_ask: Initial ask size for each strategy
            reward_add: Amount to add to ask on profitable trade
            penalty_mult: Multiplier to apply to ask on losing trade
        """
        self.num_strats = num_strats
        self.asks = [initial_ask] * num_strats
        self.reward_add = reward_add
        self.penalty_mult = penalty_mult
    
    def update(self, last_traded_pnl: List[float], aimd: List[int]) -> List[float]:
        """
        Update ask sizes based on trade PnL using AIMD.
        
        Args:
            last_traded_pnl: PnL for each strategy's last trade
            aimd: Flags indicating which strategies closed positions
            
        Returns:
            Updated asks list
        """
        for i in range(len(self.asks)):
            if last_traded_pnl[i] != 0 and aimd[i] == 1:
                if last_traded_pnl[i] > 0:
                    # Additive Increase on profit
                    self.asks[i] += self.reward_add
                else:
                    # Multiplicative Decrease on loss
                    self.asks[i] = max(1, int(self.asks[i] * self.penalty_mult))
        return self.asks
    
    def get_asks(self) -> List[float]:
        """Get current ask sizes."""
        return self.asks
