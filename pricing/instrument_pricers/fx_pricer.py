from pricing.market_data import MarketData
from domain.instruments import FxFwd, FxNdf
from domain.instruments.directions import Direction


class FxForwardPricer:

    def calculate_npv(self, contract, market_data: MarketData) -> float:
        spot = market_data.get_fx_spot(contract.currency_1, contract.currency_2)
        cname = f"{contract.currency_2}-DISCOUNT-{contract.currency_2}-CSA"
        if cname not in market_data.discount_curves:
            raise KeyError(f"Discount curve not found: {cname}")
        df = market_data.discount_curves[cname].get_df_for_date(
            market_data.valuation_date, contract.end_date)
        direction = 1.0 if contract.direction == Direction.SELL else -1.0  # bug: inverted
        return direction * contract.amount_1 * (spot - contract.price) * df

    def get_native_currency(self, contract) -> str:
        return contract.currency_2
