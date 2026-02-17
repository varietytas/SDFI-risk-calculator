from datetime import datetime
from domain.instruments import FxFwd, FxNdf, FxSwap, IRS, OIS
from domain.instruments import Direction


class InstrumentFactory:

    def from_row(self, row: dict):
        p = row["product"]
        if p == "FX Fwd": return self._build_fx_fwd(row)
        if p == "FX Ndf": return self._build_fx_ndf(row)
        if p == "FX Swap": return self._build_fx_swap(row)
        if p == "IRS": return self._build_irs(row)
        if p == "OIS": return self._build_ois(row)
        raise ValueError(f"Unsupported product: {p}.")

    def _clean_fx_fwd(self, row: dict) -> dict:  # shared cleanup for FX fwd/ndf rows
        row = row.copy()
        for k in ["product","margin","order","premium","premium_date","premium_currency","strike"]:
            row.pop(k, None)
        row["name"]              = self._ps(row.get("name"))
        row["registration_date"] = self._pd(row.get("registration_date"))
        row["start_date"]        = self._pd(row.get("start_date"))
        row["end_date"]          = self._pd(row.get("end_date"))
        row["maturity"]          = (row["end_date"] - row["start_date"]).days
        row["direction"]         = self._pdir(row.get("direction"))
        row["price"]             = self._pf(row.get("price"))
        row["currency_1"]        = self._ps(row.get("currency_1"))
        row["amount_1"]          = self._pf(row.get("amount_1"))
        row["currency_2"]        = self._ps(row.get("currency_2"))
        row["amount_2"]          = self._pf(row.get("amount_2"))
        return row

    def _build_fx_fwd(self, row):
        r = self._clean_fx_fwd(row)
        return FxFwd(name=r["name"], registration_date=r["registration_date"],
                     maturity=r["maturity"], start_date=r["start_date"],
                     end_date=r["end_date"], direction=r["direction"], price=r["price"],
                     currency_1=r["currency_1"], amount_1=r["amount_1"],
                     currency_2=r["currency_2"], amount_2=r["amount_2"])

    def _clean_fx_swap(self, row: dict) -> dict:
        r = self._clean_fx_fwd(row)
        r["rate"] = self._pf(r.get("rate"))
        return r

    def _build_fx_swap(self, row):
        r = self._clean_fx_swap(row)
        return FxSwap(name=r["name"], registration_date=r["registration_date"],
                      maturity=r["maturity"], start_date=r["start_date"],
                      end_date=r["end_date"], direction=r["direction"], price=r["price"],
                      rate=r["rate"], currency_1=r["currency_1"], amount_1=r["amount_1"],
                      currency_2=r["currency_2"], amount_2=r["amount_2"])

    def _build_fx_ndf(self, row):
        r = self._clean_fx_fwd(row)
        return FxNdf(name=r["name"], registration_date=r["registration_date"],
                     maturity=r["maturity"], start_date=r["start_date"],
                     end_date=r["end_date"], direction=r["direction"], price=r["price"],
                     currency_1=r["currency_1"], amount_1=r["amount_1"],
                     currency_2=r["currency_2"], amount_2=r["amount_2"])

    def _clean_irs(self, row: dict) -> dict:
        r = row.copy()
        for k in ["product","currency_2","amount_2","margin","order",
                  "premium","premium_date","premium_currency","strike"]:
            r.pop(k, None)
        r["name"]              = self._ps(r.get("name"))
        r["registration_date"] = self._pd(r.get("registration_date"))
        r["start_date"]        = self._pd(r.get("start_date"))
        r["end_date"]          = self._pd(r.get("end_date"))
        r["maturity"]          = (r["end_date"] - r["start_date"]).days
        r["direction"]         = self._pdir(r.get("direction"))
        r["price"]             = self._pf(r.get("price"))
        r["currency_1"]        = self._ps(r.get("currency_1"))
        r["amount_1"]          = self._pf(r.get("amount_1"))
        r["index"]             = " ".join(r["name"].split()[2:])
        return r

    def _build_irs(self, row):
        r = self._clean_irs(row)
        return IRS(name=r["name"], registration_date=r["registration_date"],
                   maturity=r["maturity"], start_date=r["start_date"],
                   end_date=r["end_date"], direction=r["direction"], price=r["price"],
                   index=r["index"], currency=r["currency_1"], amount=r["amount_1"])

    def _build_ois(self, row):
        r = self._clean_irs(row)
        return OIS(name=r["name"], registration_date=r["registration_date"],
                   maturity=r["maturity"], start_date=r["start_date"],
                   end_date=r["end_date"], direction=r["direction"], price=r["price"],
                   index=r["index"], currency=r["currency_1"], amount=r["amount_1"])

    @staticmethod
    def _pi(v): return None if v in (None,'') else int(v)

    @staticmethod
    def _ps(v): return None if v in (None, "") else str(v)

    @staticmethod
    def _pf(v): return float(str(v))

    @staticmethod
    def _pd(v):
        v = str(v)
        if v in (None, ''): return None
        return datetime.strptime(v, "%d.%m.%Y").date()

    @staticmethod
    def _pdir(v):
        if v in (None, ""): return None
        try: return Direction(v)
        except Exception: raise ValueError(f"Unknown direction: {v}.")
