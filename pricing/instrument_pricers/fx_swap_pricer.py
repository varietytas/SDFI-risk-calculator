"""
FX Swap pricer.
"""

from datetime import date
from pricing.market_data import MarketData
from domain.instruments import FxSwap
from domain.instruments.directions import Direction


class FxSwapPricer:
    """
    Prices FX Swap contracts.

    NPV Formula (per leg):
        NPV_leg = direction × amount_1 × (S_t − leg_rate) × DF_CCY2(leg_date)

    Directions:
        SELL_BUY → near: −1, far: +1
        BUY_SELL → near: +1, far: −1
    """

    def calculate_npv(self, contract: FxSwap, market_data: MarketData) -> float:
        """
        Calculate NPV for an FX Swap contract.

        Raises:
            KeyError: If required market data not found
            ValueError: If contract direction is not SELL_BUY or BUY_SELL
        """
        val_date = market_data.valuation_date

        # Contract already fully matured
        if contract.end_date <= val_date:
            return 0.0

        # Leg rates
        near_rate = contract.rate
        far_rate = contract.rate + contract.price

        # Direction signs
        if contract.direction == Direction.SELL_BUY:
            near_sign = -1.0
            far_sign = 1.0
        elif contract.direction == Direction.BUY_SELL:
            near_sign = 1.0
            far_sign = -1.0
        else:
            raise ValueError(
                f"FxSwap direction must be SELL_BUY or BUY_SELL, got: {contract.direction}"
            )

        # Spot rate and discount curve
        spot = market_data.get_fx_spot(contract.currency_1, contract.currency_2)
        curve_name = f"{contract.currency_2}-DISCOUNT-{contract.currency_2}-CSA"

        if curve_name not in market_data.discount_curves:
            raise KeyError(f"Discount curve not found: {curve_name}")

        curve = market_data.discount_curves[curve_name]

        # Near leg — skip if already settled
        if contract.start_date <= val_date:
            npv_near = 0.0
        else:
            df_near = curve.get_df_for_date(val_date, contract.start_date)
            npv_near = near_sign * contract.amount_1 * (spot - near_rate) * df_near

        # Far leg
        df_far = curve.get_df_for_date(val_date, contract.end_date)
        npv_far = far_sign * contract.amount_1 * (spot - far_rate) * df_far

        return npv_near + npv_far

    def get_native_currency(self, contract: FxSwap) -> str:  # price in CCY2
        return contract.currency_2
