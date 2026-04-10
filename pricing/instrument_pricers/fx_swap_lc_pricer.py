"""
LC pricer for FxSwap instruments.
"""

SPREAD_PCT = 0.004  # 0.4% full bid-ask spread (0.2% each side)


class FxSwapLCPricer:
    """
    Computes Liquidation Cost for FX Swap instruments using market FX Swap quotes.

    LC = 0.5 × |amount_1| × (spot + swap_points) × SPREAD_PCT
    """

    def calculate_lc(self, contract, market_data, quotes_data) -> float:
        """
        Returns LC in native currency.

        Raises:
            ValueError: If no FX Swap quote found for the currency pair.
                        LiquidationCostEngine catches this and returns None.
        """
        ccy1 = contract.currency_1
        ccy2 = contract.currency_2
        amount_1 = abs(contract.amount_1)

        tenor_days = (contract.end_date - market_data.valuation_date).days
        if tenor_days <= 0:
            return 0.0

        spot = market_data.get_fx_spot(ccy1, ccy2)
        swap_pts = quotes_data.get_swap_points(ccy1, ccy2, tenor_days)
        if swap_pts is None:
            raise ValueError(f"No FX Swap quote for {ccy1}/{ccy2}")

        return 0.5 * amount_1 * (spot + swap_pts) * SPREAD_PCT

    def get_native_currency(self, contract) -> str:
        return contract.currency_2
