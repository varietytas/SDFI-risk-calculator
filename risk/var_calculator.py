from datetime import date
from typing import List, Dict, Tuple
import numpy as np
from domain.portfolio import Portfolio
from pricing import MarketData, PricingEngine


class VaRCalculator:

    Z_VALUES = {0.90: 1.282, 0.95: 1.645, 0.99: 2.326}

    def __init__(self, portfolio: Portfolio, base_currency="RUB", data_path="data/market"):
        self.portfolio = portfolio
        self.base_currency = base_currency
        self.data_path = data_path

    def calculate_all_var(
        self, historical_dates: List[date], confidence: float = 0.95
    ) -> Tuple[List[Dict], Dict]:
        if len(historical_dates) < 2:
            raise ValueError("Need at least 2 historical dates to calculate VaR")

        contracts = list(self.portfolio)
        contract_npvs: Dict = {c: [] for c in contracts}
        portfolio_npvs: List[float] = []

        for val_date in historical_dates:
            try:
                md = MarketData.load_from_csv(val_date, self.data_path)
                engine = PricingEngine(md, self.base_currency)
                date_total = 0.0
                date_has_any = False  # track if any instrument priced on this date
                for c in contracts:
                    try:
                        npv = engine.price(c, target_currency=self.base_currency)
                        contract_npvs[c].append(npv)
                        date_total += npv
                        date_has_any = True
                    except Exception:
                        pass
                if date_has_any:
                    portfolio_npvs.append(date_total)
            except Exception:
                continue

        per_instrument = []
        for c in contracts:
            npvs = contract_npvs[c]
            if len(npvs) >= 2:
                pnls  = [npvs[i] - npvs[i-1] for i in range(1, len(npvs))]
                hist  = self._historical_var_from_pnls(pnls, confidence)
                param = self._parametric_var_from_pnls(pnls, confidence)
            else:
                hist = param = None
            per_instrument.append({"contract": c,
                                    "historical_var": hist,
                                    "parametric_var": param})

        if len(portfolio_npvs) >= 2:
            pp = [portfolio_npvs[i] - portfolio_npvs[i-1] for i in range(1, len(portfolio_npvs))]
            portfolio = {"historical_var": self._historical_var_from_pnls(pp, confidence),
                         "parametric_var": self._parametric_var_from_pnls(pp, confidence)}
        else:
            portfolio = {"historical_var": None, "parametric_var": None}

        return per_instrument, portfolio

    def _historical_var_from_pnls(self, pnls, confidence):
        sp = sorted(pnls)
        val = sp[int(len(pnls) * (1 - confidence))]
        return abs(val) if val < 0 else 0.0

    def _parametric_var_from_pnls(self, pnls, confidence):
        if confidence not in self.Z_VALUES:
            raise ValueError(f"Confidence {confidence} not supported")
        arr = np.array(pnls)
        val = np.mean(arr) - self.Z_VALUES[confidence] * np.std(arr, ddof=1)
        return abs(val) if val < 0 else 0.0
