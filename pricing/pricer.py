from pricing.market_data import MarketData
from pricing.instrument_pricers.fx_pricer import FxForwardPricer
from domain.instruments import FxFwd, FxNdf, Contract
from domain.portfolio import Portfolio


class PricingEngine:

    def __init__(self, market_data: MarketData, base_currency: str = "RUB"):
        self.market_data = market_data
        self.base_currency = base_currency
        self.fx_pricer = FxForwardPricer()
        self.pricers = {FxFwd: self.fx_pricer, FxNdf: self.fx_pricer}

    def price(self, contract: Contract, target_currency: str = None) -> float:
        ct = type(contract)
        if ct not in self.pricers:
            raise TypeError(f"No pricer registered for {ct.__name__}")
        pricer = self.pricers[ct]
        npv = pricer.calculate_npv(contract, self.market_data)
        if target_currency:
            native = pricer.get_native_currency(contract)
            return self._convert_currency(npv, native, target_currency)
        return npv

    def price_portfolio(self, portfolio: Portfolio) -> float:
        total = 0.0
        for contract in portfolio:
            total += self.price(contract, target_currency=self.base_currency)
        return total

    def _convert_currency(self, amount: float, from_ccy: str, to_ccy: str) -> float:
        if from_ccy == to_ccy: return amount
        return amount * self.market_data.get_fx_spot(from_ccy, to_ccy)

    def __repr__(self):
        return (f"PricingEngine(base_currency='{self.base_currency}', "
                f"valuation_date={self.market_data.valuation_date})")
