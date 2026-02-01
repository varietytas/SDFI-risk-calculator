from datetime import date
from typing import List
from domain.portfolio import Portfolio
from pricing import MarketData, PricingEngine


class VaRCalculator:

    def __init__(self, portfolio: Portfolio, base_currency="RUB", data_path="data/market"):
        self.portfolio = portfolio
        self.base_currency = base_currency
        self.data_path = data_path

    def calculate_historical_var(self, historical_dates: List[date], confidence=0.95):
        if len(historical_dates) < 2:
            raise ValueError("Need at least 2 historical dates")
        npvs = []
        for d in historical_dates:
            try:
                md = MarketData.load_from_csv(d, self.data_path)
                npvs.append(PricingEngine(md, self.base_currency).price_portfolio(self.portfolio))
            except Exception:
                continue
        if len(npvs) < 2:
            return None
        pnls = [npvs[i] - npvs[i-1] for i in range(1, len(npvs))]
        return self._var_from_pnls(pnls, confidence)

    def _var_from_pnls(self, pnls, confidence):
        sp = sorted(pnls)
        val = sp[int(len(pnls) * (1 - confidence))]
        return abs(val) if val < 0 else 0.0
