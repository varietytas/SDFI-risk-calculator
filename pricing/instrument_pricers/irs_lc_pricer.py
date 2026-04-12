"""
LC pricer for IRS and OIS instruments.

Formula:
    LC = 0.5 × N × R_quoted × τ × DF(T) × SPREAD_PCT

Where:
    N          = notional (contract.amount)
    R_quoted   = nearest-tenor mid-rate
    τ          = remaining life in years (Act/365)
    DF(T)      = discount factor
    SPREAD_PCT = 0.004  (0.4% full bid-ask spread)
"""

SPREAD_PCT = 0.004  # 0.2% each side


class IRSwapLCPricer:
    """
    Computes LC for IRS and OIS.
    """

    def calculate_lc(self, contract, market_data, quotes_data) -> float:
        """
        Returns LC in native currency.

        Raises:
            ValueError: If no matching quote found.
                        LiquidationCostEngine catches this and returns None.
        """
        tenor_days = (contract.end_date - market_data.valuation_date).days
        if tenor_days <= 0:
            return 0.0

        tau = tenor_days / 365.0

        # Discount factor
        disc_name = f"{contract.currency}-DISCOUNT-{contract.currency}-CSA"
        df = market_data.discount_curves[disc_name].get_df_for_date(
            market_data.valuation_date, contract.end_date
        )

        # Market mid-rate from quotes
        r_quoted = quotes_data.get_irs_rate(contract.product, contract.index, tenor_days)
        if r_quoted is None:
            raise ValueError(
                f"No {contract.product} quote for index '{contract.index}'"
            )

        return 0.5 * abs(contract.amount) * r_quoted * tau * df * SPREAD_PCT

    def get_native_currency(self, contract) -> str:
        return contract.currency
