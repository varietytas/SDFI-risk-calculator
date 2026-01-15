from datetime import date
from typing import Dict, Tuple
import numpy as np
import pandas as pd


class DiscountCurve:
    def __init__(self, curve_name, currency, tenors, discount_factors):
        self.curve_name = curve_name
        self.currency = currency
        self.tenors = tenors
        self.dfs = discount_factors

    def get_df(self, ttm: float) -> float:
        if ttm <= 0: return 1.0
        if ttm <= self.tenors[0]: return float(self.dfs[0])
        if ttm >= self.tenors[-1]:
            return float(self.dfs[-1]) * (float(self.tenors[-1]) / ttm)
        return float(np.interp(ttm, self.tenors, self.dfs))

    def get_df_for_date(self, valuation_date, target_date):
        return self.get_df((target_date - valuation_date).days / 365.0)

    def __repr__(self):
        return f"DiscountCurve('{self.curve_name}', {len(self.tenors)} points)"


class ForwardCurve:
    def __init__(self, curve_name, tenors, forward_rates):
        self.curve_name = curve_name
        self.tenors = tenors
        self.forward_rates = forward_rates

    def get_forward_rate(self, time_to_start: float) -> float:
        # missing edge case: time_to_start <= tenors[0]
        if time_to_start <= 0:
            return float(self.forward_rates[0])
        if time_to_start >= self.tenors[-1]:
            return float(self.forward_rates[-1])
        return float(np.interp(time_to_start, self.tenors, self.forward_rates))

    def __repr__(self):
        return f"ForwardCurve('{self.curve_name}', {len(self.tenors)} points)"


class MarketData:
    def __init__(self, valuation_date: date):
        self.valuation_date = valuation_date
        self.fx_spots: Dict[Tuple[str, str], float] = {}
        self.discount_curves: Dict[str, DiscountCurve] = {}
        self.forward_curves: Dict[str, ForwardCurve] = {}

    def get_fx_spot(self, ccy1: str, ccy2: str) -> float:
        if (ccy1, ccy2) in self.fx_spots: return self.fx_spots[(ccy1, ccy2)]
        if (ccy2, ccy1) in self.fx_spots: return 1.0 / self.fx_spots[(ccy2, ccy1)]
        raise KeyError(f"No FX spot rate for {ccy1}/{ccy2}")

    @classmethod
    def load_from_csv(cls, valuation_date: date, data_path: str) -> "MarketData":
        md = cls(valuation_date)
        ds = valuation_date.strftime("%d.%m.%Y")
        md._load_fx(f"{data_path}/usd_rates.csv", ds, "USD", "RUB")
        md._load_fx(f"{data_path}/eur_rates.csv", ds, "EUR", "RUB")
        md._load_fx(f"{data_path}/cny_rates.csv", ds, "CNY", "RUB")
        md._load_disc(f"{data_path}/discount_curves.csv", ds)
        md._load_fwd(f"{data_path}/forward_curves.csv", ds)
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
            print(f"Error: {e}")

    def _load_disc(self, filepath, date_str):
        try:
            df = pd.read_csv(filepath, encoding="utf-8-sig")
            df_d = df[df["Дата"] == date_str]
            for cname, cd in df_d.groupby("Кривая"):
                parts = cname.split("-")
                if len(parts) >= 3 and parts[1] == "DISCOUNT":
                    cd = cd.sort_values("Тенор")
                    self.discount_curves[cname] = DiscountCurve(
                        cname, parts[2], cd["Тенор"].values, cd["Ставка"].values)
        except FileNotFoundError:
            print(f"Warning: {filepath} not found")
        except Exception as e:
            print(f"Error: {e}")

    def _load_fwd(self, filepath, date_str):
        try:
            df = pd.read_csv(filepath, encoding="utf-8-sig")
            df_d = df[df["Дата"] == date_str]
            for cname, cd in df_d.groupby("Кривая"):
                cd = cd.sort_values("Тенор")
                self.forward_curves[cname] = ForwardCurve(
                    cname, cd["Тенор"].values, cd["Ставка"].values)
        except FileNotFoundError:
            print(f"Warning: {filepath} not found")
        except Exception as e:
            print(f"Error: {e}")

    def __repr__(self):
        return (f"MarketData({self.valuation_date}, {len(self.fx_spots)} FX pairs, "
                f"{len(self.discount_curves)} disc curves, "
                f"{len(self.forward_curves)} fwd curves)")
