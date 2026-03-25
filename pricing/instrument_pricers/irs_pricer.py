"""
IRS and OIS pricer.

NPV formula:
    NPV = direction × N × (R_fixed − f(T)) × τ × DF(T)

Where:
    direction = +1 for Receive Fixed, −1 for Pay Fixed
    N         = notional amount
    R_fixed   = contractual fixed rate as decimal
    f(T)      = forward/OIS rate at remaining tenor T from the index curve
    τ         = remaining life in years  (Act/365)
    DF(T)     = discount factor to maturity
"""

from pricing.market_data import MarketData
from domain.instruments.directions import Direction


# Maps substrings of contract.index to forward curve names
INDEX_CURVE_MAP = [
    # CNY-specific — must precede generic 'rusfar'
    ('rusfarcny',       'CNY-RUSFARCNY-OIS-COMPOUND'),
    ('cny repo',        'CNY-REPO-RATE'),
    # RUB RUONIA variants — specific before generic
    ('ruonia avg',      'RUB-RUONIA-OIS-AVG'),
    ('ruonia comp',     'RUB-RUONIA-OIS-COMPOUND'),
    # RUB RUSFAR variants
    ('rusfar 3m',       'RUB-RUSFAR-3M'),
    ('rusfar',          'RUB-RUSFAR-OIS-COMPOUND'),
    # RUB Key Rate
    ('keyrate',         'RUB-CBR-KEY-RATE'),
    ('key rate',        'RUB-CBR-KEY-RATE'),
    ('key-rate',        'RUB-CBR-KEY-RATE'),
    # EUR curves
    ('euribor 6m',      'EUR-EURIBOR-Act/365-6M'),
    ('euribor 1m',      'EUR-EURIBOR-Act/365-1M'),
    ('euribor 3m',      'EUR-EURIBOR-Act/365-3M'),
    ('euribor',         'EUR-EURIBOR-Act/365-3M'),   # default EURIBOR → 3M
    ('estr',            'EUR-ESTR'),
    # USD
    ('sofr',            'USD-SOFR'),
    # CNY fallback
    ('repo',            'CNY-REPO-RATE'),
]


def _get_forward_curve_name(index: str) -> str:
    """
    Map contract.index to a forward curve name via case-insensitive substring match.
    """
    idx_lower = index.lower()
    for keyword, curve_name in INDEX_CURVE_MAP:
        if keyword in idx_lower:
            return curve_name
    raise KeyError(
        f"No forward curve mapping for index: '{index}'. "
        f"Add an entry to INDEX_CURVE_MAP in irs_pricer.py."
    )


class IRSwapPricer:
    """
    Prices IRS and OIS contracts.
    """

    def calculate_npv(self, contract, market_data: MarketData) -> float:
        """
        Calculate NPV for an IRS/OIS contract.

        Raises:
            KeyError  : If a required curve is absent from market_data
            ValueError: If the contract has already matured (returns 0.0)
        """
        # Remaining life in years (Act/365)
        tau = (contract.end_date - market_data.valuation_date).days / 365.0

        if tau <= 0:
            return 0.0

        # -- Discount factor --
        disc_name = f"{contract.currency}-DISCOUNT-{contract.currency}-CSA"
        if disc_name not in market_data.discount_curves:
            raise KeyError(f"Discount curve not found: {disc_name}")
        df = market_data.discount_curves[disc_name].get_df_for_date(
            market_data.valuation_date, contract.end_date
        )

        # -- Forward / OIS rate at remaining tenor --
        fwd_name = _get_forward_curve_name(contract.index)
        if fwd_name not in market_data.forward_curves:
            raise KeyError(f"Forward curve not found: {fwd_name}")
        f = market_data.forward_curves[fwd_name].get_forward_rate(tau)

        # -- Direction --
        direction = 1.0 if contract.direction == Direction.RECIEVE_FIX else -1.0

        return direction * contract.amount * (contract.price - f) * tau * df

    def get_native_currency(self, contract) -> str:
        return contract.currency
