"""
Value at Risk (VaR) calculator implementing historical and parametric methods.
Based on formulas from formulas.xlsx.
"""

from datetime import date
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np
from domain.portfolio import Portfolio
from pricing import MarketData, PricingEngine, QuotesData, LiquidationCostEngine


class VaRCalculator:
    """
    Calculates VaR using historical and parametric methods.
    """

    Z_VALUES = {0.90: 1.282, 0.95: 1.645, 0.99: 2.326}

    # φ(z) / (1 − confidence) — precomputed ES coefficients under normal distribution
    ES_COEFFICIENTS = {0.90: 1.7550, 0.95: 2.0628, 0.99: 2.6652}

    def __init__(
            self,
            portfolio: Portfolio,
            base_currency: str = 'RUB',
            data_path: str = 'data/market'
        ):
        self.portfolio = portfolio
        self.base_currency = base_currency
        self.data_path = data_path

    # Efficient multi-instrument breakdown — single pass

    def calculate_all_var(
        self,
        historical_dates: List[date],
        confidence: float = 0.95,
    ) -> Tuple[List[Dict], Dict]:
        """
        Calculate VaR for every individual instrument AND the whole portfolio
        in a single pass through historical dates.

        Returns:
            Tuple of:
            - per_instrument: list of dicts, one per contract:
                {'contract':        Contract,
                 'historical_var':  float | None,
                 'parametric_var':  float | None,
                 'historical_es':   float | None,
                 'parametric_es':   float | None,
                 'lc':              float | None,
                 'historical_lvar': float | None,
                 'parametric_lvar': float | None}
            - portfolio: dict with the same seven keys
        """

        if len(historical_dates) < 2:
            raise ValueError("Need at least 2 historical dates to calculate VaR")

        contracts = list(self.portfolio)

        # NPV series per contract across all valid dates
        contract_npvs: Dict = {c: [] for c in contracts}
        portfolio_npvs: List[float] = []
        last_market_data = None

        for val_date in historical_dates:
            try:
                market_data = MarketData.load_from_csv(val_date, self.data_path)
                engine = PricingEngine(market_data, self.base_currency)

                date_npvs = {}
                for contract in contracts:
                    try:
                        npv = engine.price(contract, target_currency=self.base_currency)
                        date_npvs[contract] = npv
                    except Exception:
                        date_npvs[contract] = None

                # Record each instrument's NPV independently
                date_total = 0.0
                date_has_any = False
                for contract, npv in date_npvs.items():
                    if npv is not None:
                        contract_npvs[contract].append(npv)
                        date_total += npv
                        date_has_any = True

                if date_has_any:
                    portfolio_npvs.append(date_total)
                    last_market_data = market_data

            except Exception:
                continue

        # Build LiquidationCostEngine
        lc_engine = None
        if last_market_data is not None:
            quotes_data = QuotesData.load_from_csv(str(Path(self.data_path) / 'quotes.csv'))
            lc_engine = LiquidationCostEngine(last_market_data, quotes_data, self.base_currency)

        # Per-instrument VaR + LC
        per_instrument = list()
        for contract in contracts:
            npvs = contract_npvs[contract]
            lc = lc_engine.compute_lc(contract, self.base_currency) if lc_engine else None
            if len(npvs) >= 2:
                pnls  = [npvs[i] - npvs[i-1] for i in range(1, len(npvs))]
                hist  = self._historical_var_from_pnls(pnls, confidence)
                param = self._parametric_var_from_pnls(pnls, confidence)
                h_es  = self._historical_es_from_pnls(pnls, confidence)
                p_es  = self._parametric_es_from_pnls(pnls, confidence)
            else:
                hist = param = h_es = p_es = None
            per_instrument.append({
                'contract':        contract,
                'historical_var':  hist,
                'parametric_var':  param,
                'historical_es':   h_es,
                'parametric_es':   p_es,
                'lc':              lc,
                'historical_lvar': (hist + lc) if (hist is not None and lc is not None) else None,
                'parametric_lvar': (param + lc) if (param is not None and lc is not None) else None,
            })

        # Portfolio LC
        lcs = [r['lc'] for r in per_instrument if r['lc'] is not None]
        portfolio_lc = sum(lcs) if lcs else None

        # Portfolio VaR + LC
        if len(portfolio_npvs) >= 2:
            port_pnls = [portfolio_npvs[i] - portfolio_npvs[i-1] for i in range(1, len(portfolio_npvs))]
            p_hist = self._historical_var_from_pnls(port_pnls, confidence)
            p_param = self._parametric_var_from_pnls(port_pnls, confidence)
            _arr = np.array(port_pnls)
            portfolio = {
                'historical_var':  p_hist,
                'parametric_var':  p_param,
                'historical_es':   self._historical_es_from_pnls(port_pnls, confidence),
                'parametric_es':   self._parametric_es_from_pnls(port_pnls, confidence),
                'lc':              portfolio_lc,
                'historical_lvar': (p_hist + portfolio_lc) if (p_hist is not None and portfolio_lc is not None) else None,
                'parametric_lvar': (p_param + portfolio_lc) if (p_param is not None and portfolio_lc is not None) else None,
                'pnl_mean':        float(np.mean(_arr)),
                'pnl_std':         float(np.std(_arr, ddof=1)),
            }
        else:
            portfolio = {
                'historical_var': None, 'parametric_var': None,
                'historical_es':  None, 'parametric_es':  None,
                'lc':             portfolio_lc,
                'historical_lvar': None, 'parametric_lvar': None,
                'pnl_mean':       None, 'pnl_std':         None,
            }

        return per_instrument, portfolio

    # √T scaling

    @staticmethod
    def scale_var(
        per_instrument: List[Dict],
        portfolio: Dict,
        holding_period: int,
    ) -> Tuple[List[Dict], Dict]:
        """
        Scale 1-day VaR results to a longer holding period using VaR_T = VaR_1day × √T

        Returns:
            Scaled copies of per_instrument and portfolio dicts.
        """

        factor = holding_period ** 0.5

        def _scale(x):
            return x * factor if x is not None else None

        def _lvar(var_scaled, lc):
            return (var_scaled + lc) if (var_scaled is not None and lc is not None) else None

        scaled_instruments = [
            {
                'contract':        r['contract'],
                'historical_var':  _scale(r['historical_var']),
                'parametric_var':  _scale(r['parametric_var']),
                'historical_es':   _scale(r['historical_es']),
                'parametric_es':   _scale(r['parametric_es']),
                'lc':              r.get('lc'),  # Not scaled — fixed one-time cost
                'historical_lvar': _lvar(_scale(r['historical_var']), r.get('lc')),
                'parametric_lvar': _lvar(_scale(r['parametric_var']), r.get('lc')),
            }
            for r in per_instrument
        ]

        lc = portfolio.get('lc')
        h = _scale(portfolio['historical_var'])
        p = _scale(portfolio['parametric_var'])
        scaled_portfolio = {
            'historical_var':  h,
            'parametric_var':  p,
            'historical_es':   _scale(portfolio['historical_es']),
            'parametric_es':   _scale(portfolio['parametric_es']),
            'lc':              lc,  # Not scaled
            'historical_lvar': _lvar(h, lc),
            'parametric_lvar': _lvar(p, lc),
            'pnl_mean':        portfolio.get('pnl_mean'),  # 1-day stats, not scaled
            'pnl_std':         portfolio.get('pnl_std'),
        }

        return scaled_instruments, scaled_portfolio

    # Private helpers

    def _historical_es_from_pnls(self, pnls: List[float], confidence: float) -> float:
        """Mean loss in the tail beyond the VaR cutoff"""

        sorted_pnls = sorted(pnls)
        k = int(len(pnls) * (1 - confidence))
        tail = sorted_pnls[0 : max(1, k)]
        mean_tail = sum(tail) / len(tail)

        return abs(mean_tail) if mean_tail < 0 else 0.0

    def _parametric_es_from_pnls(self, pnls: List[float], confidence: float) -> float:
        """ES under normal distribution"""

        if confidence not in self.ES_COEFFICIENTS:
            raise ValueError(f"Confidence level {confidence} not supported. Use 0.90, 0.95, or 0.99")
        pnls_array = np.array(pnls)
        mean_pnl = np.mean(pnls_array)
        std_pnl = np.std(pnls_array, ddof=1)
        es_value = mean_pnl - std_pnl * self.ES_COEFFICIENTS[confidence]

        return abs(es_value) if es_value < 0 else 0.0

    def _historical_var_from_pnls(self, pnls: List[float], confidence: float) -> float:
        """Apply historical simulation formula to a pre-computed P&L series"""

        sorted_pnls = sorted(pnls)
        index = int(len(pnls) * (1 - confidence))
        var_value = sorted_pnls[index]

        return abs(var_value) if var_value < 0 else 0.0

    def _parametric_var_from_pnls(self, pnls: List[float], confidence: float) -> float:
        """Apply parametric formula to a pre-computed P&L series"""

        if confidence not in self.Z_VALUES:
            raise ValueError(f"Confidence level {confidence} not supported. Use 0.90, 0.95, or 0.99")
        pnls_array = np.array(pnls)
        mean_pnl = np.mean(pnls_array)
        std_pnl = np.std(pnls_array, ddof=1)
        z = self.Z_VALUES[confidence]
        var_value = mean_pnl - z * std_pnl

        return abs(var_value) if var_value < 0 else 0.0
