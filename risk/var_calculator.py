from datetime import date
from typing import List
import numpy as np
from domain.portfolio import Portfolio
from pricing import MarketData, PricingEngine


class VaRCalculator:

    Z_VALUES = {0.90: 1.282, 0.95: 1.645, 0.99: 2.326}

    def __init__(self, portfolio: Portfolio, base_currency="RUB", data_path="data/market"):
        self.portfolio = portfolio
        self.base_currency = base_currency
        self.data_path = data_path

    def _npv_series(self, historical_dates):
        npvs = []
        for d in historical_dates:
            try:
                md = MarketData.load_from_csv(d, self.data_path)
                npvs.append(PricingEngine(md, self.base_currency).price_portfolio(self.portfolio))
            except Exception:
                continue
        return npvs

    def calculate_historical_var(self, historical_dates: List[date], confidence=0.95):
        if len(historical_dates) < 2:
            raise ValueError("Need at least 2 historical dates")
        npvs = self._npv_series(historical_dates)
        if len(npvs) < 2: return None
        pnls = [npvs[i] - npvs[i-1] for i in range(1, len(npvs))]
        return self._historical_var_from_pnls(pnls, confidence)

    def calculate_parametric_var(self, historical_dates: List[date], confidence=0.95):
        if len(historical_dates) < 2:
            raise ValueError("Need at least 2 historical dates")
        npvs = self._npv_series(historical_dates)
        if len(npvs) < 2: return None
        pnls = [npvs[i] - npvs[i-1] for i in range(1, len(npvs))]
        return self._parametric_var_from_pnls(pnls, confidence)

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
