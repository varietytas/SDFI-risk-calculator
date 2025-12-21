from enum import Enum

class Direction(Enum):
    BUY         = 'Buy'             # For FxFwd and FxNdf
    SELL        = 'Sell'
    SELL_BUY    = 'Sell/Buy'        # For FxSwap
    BUY_SELL    = 'Buy/Sell'
    PAY_FIX     = 'Pay Fixed'       # For IRS/OIS and Option
    RECIEVE_FIX = 'Receive Fixed'

    def __invert__(self):
        opposites = {
            self.BUY: self.SELL,
            self.SELL: self.BUY,
            self.SELL_BUY: self.BUY_SELL,
            self.BUY_SELL: self.SELL_BUY,
            self.PAY_FIX: self.RECEIVE_FIX,
            self.RECEIVE_FIX: self.PAY_FIX,
        }
        return opposites[self]