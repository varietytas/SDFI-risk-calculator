"""
FX Fwd and FX Ndf pricer.
"""

from datetime import date
from pricing.market_data import MarketData
from domain.instruments import FxFwd, FxNdf
from domain.instruments.directions import Direction


class FxForwardPricer:
    """
    Prices FX Fwd and FX Ndf contracts.

    NPV Formula:
        NPV = Direction × Amount_1 × (S_t - K) × DF(T)

    Where:
        - S_t = Current FX spot rate (currency_1/currency_2)
        - K = Contract forward rate (strike)
        - DF(T) = Discount factor to maturity in currency_2
        - Direction = +1 for BUY, -1 for SELL
    """

    def calculate_npv(self, contract: FxFwd | FxNdf, market_data: MarketData) -> float:
        """
        Calculate NPV for a contract.

        Raises:
            KeyError: If required market data not found
        """

        # Get FX spot rate
        spot_rate = market_data.get_fx_spot(contract.currency_1, contract.currency_2)

        # Get discount factor to maturity
        curve_name = f"{contract.currency_2}-DISCOUNT-{contract.currency_2}-CSA"

        if curve_name not in market_data.discount_curves:
            raise KeyError(f'Discount curve not found: {curve_name}')

        curve = market_data.discount_curves[curve_name]
        df = curve.get_df_for_date(market_data.valuation_date, contract.end_date)

        direction = 1.0 if contract.direction == Direction.BUY else -1.0

        return direction * contract.amount_1 * (spot_rate - contract.price) * df

    def get_native_currency(self, contract: FxFwd | FxNdf) -> str:
        return contract.currency_2
