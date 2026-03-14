from pricing.market_data import MarketData
from domain.instruments.directions import Direction


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
        # TODO: forward curve lookup
        f = 0.0
        direction = 1.0 if contract.direction == Direction.RECIEVE_FIX else -1.0
        return direction * contract.amount * (contract.price - f) * tau * df

    def get_native_currency(self, contract) -> str:
        return contract.currency
