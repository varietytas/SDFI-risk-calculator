from pricing.market_data import MarketData
from domain.instruments.directions import Direction


INDEX_CURVE_MAP = [
    ('ruonia avg',  'RUB-RUONIA-OIS-AVG'),
    ('ruonia comp', 'RUB-RUONIA-OIS-COMPOUND'),
    ('rusfar 3m',   'RUB-RUSFAR-3M'),
    ('rusfar',      'RUB-RUSFAR-OIS-COMPOUND'),
    ('euribor 3m',  'EUR-EURIBOR-Act/365-3M'),
    ('euribor',     'EUR-EURIBOR-Act/365-3M'),
    ('sofr',        'USD-SOFR'),
]


def _get_forward_curve_name(index: str) -> str:
    idx_lower = index.lower()
    for keyword, curve_name in INDEX_CURVE_MAP:
        if keyword in idx_lower:
            return curve_name
    raise KeyError(f"No forward curve mapping for index: '{index}'")


class IRSwapPricer:

    def calculate_npv(self, contract, market_data: MarketData) -> float:
        tau = (contract.end_date - market_data.valuation_date).days / 365.0
        if tau <= 0:
            return 0.0
        disc_name = f"{contract.currency}-DISCOUNT-{contract.currency}-CSA"
        if disc_name not in market_data.discount_curves:
            raise KeyError(f"Discount curve not found: {disc_name}")
        df = market_data.discount_curves[disc_name].get_df_for_date(
            market_data.valuation_date, contract.end_date)
        fwd_name = _get_forward_curve_name(contract.index)
        if fwd_name not in market_data.forward_curves:
            raise KeyError(f"Forward curve not found: {fwd_name}")
        f = market_data.forward_curves[fwd_name].get_forward_rate(tau)
        direction = 1.0 if contract.direction == Direction.RECIEVE_FIX else -1.0
        return direction * contract.amount * (contract.price - f) * tau * df

    def get_native_currency(self, contract) -> str:
        return contract.currency
