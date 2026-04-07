"""
Computes Liquidation Cost (LC) per instrument.

To add LC support for a new instrument type:
  1. Create a new LCPricer in instrument_pricers/ implementing
     calculate_lc(contract, market_data, quotes_data) -> float
     get_native_currency(contract) -> str
  2. Register it in LiquidationCostEngine.__init__
"""

from domain.instruments import FxFwd, FxNdf, FxSwap, IRS, OIS
from pricing.instrument_pricers.fx_fwd_lc_pricer import FxForwardLCPricer
from pricing.instrument_pricers.fx_swap_lc_pricer import FxSwapLCPricer
from pricing.instrument_pricers.irs_lc_pricer import IRSwapLCPricer


class LiquidationCostEngine:
    """
    Dispatches LC calculation to the appropriate instrument-specific pricer.
    """

    def __init__(self, market_data, quotes_data, base_currency: str = 'RUB'):
        self.market_data = market_data
        self.quotes_data = quotes_data
        self.base_currency = base_currency

        fwd_lc = FxForwardLCPricer()
        fx_swap_lc = FxSwapLCPricer()
        irs_lc = IRSwapLCPricer()
        self.pricers = {
            FxFwd:  fwd_lc,
            FxNdf:  fwd_lc,
            FxSwap: fx_swap_lc,
            IRS:    irs_lc,
            OIS:    irs_lc,
        }

    def compute_lc(self, contract, target_currency: str = None) -> float | None:
        """
        Return LC for contract, or None if:
          - instrument type has no registered pricer, or
          - no market quote is available for the currency pair.
        """

        target_currency = target_currency or self.base_currency
        pricer = self.pricers.get(type(contract))
        if pricer is None:
            return None

        try:
            lc = pricer.calculate_lc(contract, self.market_data, self.quotes_data)
        except Exception:
            return None

        native = pricer.get_native_currency(contract)
        if native != target_currency:
            lc *= self.market_data.get_fx_spot(native, target_currency)

        return lc
