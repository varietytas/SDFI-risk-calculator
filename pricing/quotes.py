"""
Quotes data — mid-rates used for Liquidation Cost calculation.
"""

import pandas as pd


TENOR_DAYS = {
    '1D': 1, '1W': 7, '2W': 14, '1M': 30, '2M': 60, '3M': 90,
    '6M': 180, '9M': 270, '1Y': 365, '18M': 548, '2Y': 730, '3Y': 1095,
    '4Y': 1460, '5Y': 1825, '6Y': 2190, '7Y': 2555, '8Y': 2920,
    '9Y': 3285, '10Y': 3650,
}


class QuotesData:
    """
    Container for market quotes loaded from quotes.csv.
    """

    def __init__(self, df: pd.DataFrame):
        self._df = df


    @classmethod
    def load_from_csv(cls, quotes_path: str) -> 'QuotesData':
        df = pd.read_csv(quotes_path, encoding='utf-8-sig')
        return cls(df)


    def get_swap_points(self, ccy1: str, ccy2: str, tenor_days: int) -> float | None:
        """
        Return FX swap points for the nearest available tenor, or None if not found.
        """

        fx_swaps = self._df[self._df['Продукт'] == 'FX Swap']
        subset = fx_swaps[fx_swaps['Инструмент'].str.contains(f"{ccy1}/{ccy2}", na=False)]
        if subset.empty:
            return None

        subset = subset.copy()
        subset['_days'] = subset['Срок'].map(TENOR_DAYS)
        subset = subset.dropna(subset=['_days'])
        if subset.empty:
            return None

        idx = (subset['_days'] - tenor_days).abs().idxmin()
        return float(subset.loc[idx, 'Котировка'])


    def get_fwd_spread(self, product: str, ccy1: str, ccy2: str, tenor_days: int) -> float | None:
        """
        Return the FX Forward bid-ask spread for the nearest available tenor, or None if not found.
        """

        by_product = self._df[self._df['Продукт'] == product]
        subset = by_product[by_product['Инструмент'].str.contains(f"{ccy1}/{ccy2}", na=False)]
        if subset.empty:
            return None

        subset = subset.copy()
        subset['_days'] = subset['Срок'].map(TENOR_DAYS)
        subset = subset.dropna(subset=['_days'])
        if subset.empty:
            return None

        idx = (subset['_days'] - tenor_days).abs().idxmin()
        return float(subset.loc[idx, 'Котировка'])


    def get_irs_rate(self, product: str, index: str, tenor_days: int) -> float | None:
        """
        Return mid-rate for the nearest available tenor for an IRS or OIS quote,
        or None if no matching instrument is found.
        """
        
        by_product = self._df[self._df['Продукт'] == product]
        index_lower = index.lower()
        subset = by_product[
            by_product['Инструмент'].str.lower().str.contains(index_lower, na=False)
        ]
        if subset.empty:
            return None

        subset = subset.copy()
        subset['_days'] = subset['Срок'].map(TENOR_DAYS)
        subset = subset.dropna(subset=['_days'])
        if subset.empty:
            return None

        idx = (subset['_days'] - tenor_days).abs().idxmin()
        return float(subset.loc[idx, 'Котировка'])
