"""
Main pricing engine for calculating NPV of instruments and portfolios.
"""

from pricing.market_data import MarketData
from pricing.instrument_pricers.fx_pricer import FxForwardPricer
from pricing.instrument_pricers.fx_swap_pricer import FxSwapPricer
from pricing.instrument_pricers.irs_pricer import IRSwapPricer
from domain.instruments import FxFwd, FxNdf, FxSwap, IRS, OIS, Contract
from domain.portfolio import Portfolio


class PricingEngine:
    """
    Delegates to instrument-specific pricers.
    Handles base currency conversion for portfolio aggregation.
    """

    def __init__(self, market_data: MarketData, base_currency: str = 'RUB'):
        self.market_data = market_data
        self.base_currency = base_currency

        # Register pricers
        self.fx_pricer      = FxForwardPricer()
        self.fx_swap_pricer = FxSwapPricer()
        self.irs_pricer     = IRSwapPricer()

        # Map types to pricers
        self.pricers = {
            FxFwd:  self.fx_pricer,
            FxNdf:  self.fx_pricer,
            FxSwap: self.fx_swap_pricer,
            IRS:    self.irs_pricer,
            OIS:    self.irs_pricer,
        }


    def price(self, contract: Contract, target_currency: str = None) -> float:
        """
        Calculate NPV for a single contract.

        Raises:
            TypeError: If no pricer registered for contract type
            KeyError: If required market data not found
        """

        contract_type = type(contract)
        if contract_type not in self.pricers:
            raise TypeError(f'No pricer registered for contract type: {contract_type.__name__}')
        pricer = self.pricers[contract_type]

        npv_native = pricer.calculate_npv(contract, self.market_data)

        if target_currency:
            native_ccy = pricer.get_native_currency(contract)
            return self._convert_currency(npv_native, native_ccy, target_currency)

        return npv_native


    def price_portfolio(self, portfolio: Portfolio) -> float:
        """
        Calculate total portfolio NPV in base currency.

        Raises:
            TypeError: If any contract type has no registered pricer
            KeyError: If required market data not found
        """

        total_npv = 0.0

        for contract in portfolio:
            npv = self.price(contract, target_currency=self.base_currency)
            total_npv += npv

        return total_npv


    def _convert_currency(self, amount: float, from_ccy: str, to_ccy: str) -> float:
        """
        Convert amount from one currency to another using spot rates.

        Raises:
            KeyError: If FX rate not found
        """

        if from_ccy == to_ccy:
            return amount

        fx_rate = self.market_data.get_fx_spot(from_ccy, to_ccy)
        return amount * fx_rate


    def __repr__(self):
        return (f"PricingEngine(base_currency='{self.base_currency}', "
                f"valuation_date={self.market_data.valuation_date})")
