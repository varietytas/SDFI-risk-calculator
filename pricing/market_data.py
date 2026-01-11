from datetime import date
from typing import Dict, Tuple
import pandas as pd


class MarketData:
    def __init__(self, valuation_date: date):
        self.valuation_date = valuation_date
        self.fx_spots: Dict[Tuple[str, str], float] = {}

    def get_fx_spot(self, ccy1: str, ccy2: str) -> float:
        if (ccy1, ccy2) in self.fx_spots:
            return self.fx_spots[(ccy1, ccy2)]
        if (ccy2, ccy1) in self.fx_spots:
            return 1.0 / self.fx_spots[(ccy2, ccy1)]
        raise KeyError(f"No FX spot rate for {ccy1}/{ccy2} on {self.valuation_date}")

    @classmethod
    def load_from_csv(cls, valuation_date: date, data_path: str) -> "MarketData":
        md = cls(valuation_date)
        ds = valuation_date.strftime("%d.%m.%Y")
        md._load_fx(f"{data_path}/usd_rates.csv", ds, "USD", "RUB")
        md._load_fx(f"{data_path}/eur_rates.csv", ds, "EUR", "RUB")
        md._load_fx(f"{data_path}/cny_rates.csv", ds, "CNY", "RUB")
        return md

    def _load_fx(self, filepath, date_str, ccy1, ccy2):
        try:
            df = pd.read_csv(filepath, sep=";", encoding="utf-8-sig")
            row = df[df["data"] == date_str]
            if not row.empty:
                rate = float(str(row.iloc[0]["curs"]).replace(",", "."))
                self.fx_spots[(ccy1, ccy2)] = rate
                self.fx_spots[(ccy2, ccy1)] = 1.0 / rate
        except FileNotFoundError:
            print(f"Warning: {filepath} not found")
        except Exception as e:
            print(f"Error loading FX rates: {e}")

    def __repr__(self):
        return f"MarketData({self.valuation_date}, {len(self.fx_spots)} FX pairs)"
