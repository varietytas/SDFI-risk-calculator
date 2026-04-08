"""
LC pricer for FX Forward and FX NDF instruments.

Formula:
    LC = 0.5 × |Amount_1| × bid_ask_spread
"""


class FxForwardLCPricer:
    """
    Computes Liquidation Cost for FX Forward and FX NDF instruments.
    """

    def calculate_lc(self, contract, market_data, quotes_data) -> float:
        """
        Returns LC in native currency (contract.currency_2).

        Raises:
            ValueError: If no spread quote found for the currency pair.
                        LiquidationCostEngine catches this and returns None.
        """
        tenor_days = (contract.end_date - market_data.valuation_date).days
        if tenor_days <= 0:
            return 0.0

        spread = quotes_data.get_fwd_spread(
            contract.product, contract.currency_1, contract.currency_2, tenor_days
        )
        if spread is None:
            raise ValueError(
                f"No {contract.product} spread quote for {contract.currency_1}/{contract.currency_2}"
            )

        return 0.5 * abs(contract.amount_1) * spread

    def get_native_currency(self, contract) -> str:
        return contract.currency_2
