from pricing.market_data import MarketData
from pricing.instrument_pricers.fx_pricer import FxForwardPricer
from domain.instruments import FxFwd, FxNdf, Contract


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
            if native != target_currency:
                npv *= self.market_data.get_fx_spot(native, target_currency)
        return npv
