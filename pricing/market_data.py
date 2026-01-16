'''
Market data classes for loading and accessing FX rates, discount curves, and forward curves.
'''

from datetime import date
from typing import Dict, Tuple
import numpy as np
import pandas as pd


class DiscountCurve:
    '''
    Discount curve with linear interpolation.
    Stores discount factors by tenor (in years from valuation date).
    '''

    def __init__(
            self,
            curve_name: str,
            currency: str,
            tenors: np.ndarray,
            discount_factors: np.ndarray
        ):
        self.curve_name = curve_name
        self.currency = currency
        self.tenors = tenors  # Array of tenors in years (e.g., 0.0833, 0.25, 0.5, 1, 2, 3...)
        self.dfs = discount_factors  # Corresponding discount factors

    def get_df(self, time_to_maturity: float) -> float:
        '''
        Get discount factor for a given time to maturity (in years).
        Uses linear interpolation between points.
        '''

        if time_to_maturity <= 0:
            return 1.0

        if time_to_maturity <= self.tenors[0]:
            return self.dfs[0]

        if time_to_maturity >= self.tenors[-1]:
            # Extrapolate using last rate
            return self.dfs[-1] * (self.tenors[-1] / time_to_maturity)

        # Linear interpolation
        return np.interp(time_to_maturity, self.tenors, self.dfs)

    def get_df_for_date(self, valuation_date: date, target_date: date) -> float:
        '''
        Get discount factor from valuation_date to target_date.
        '''

        days_to_maturity = (target_date - valuation_date).days
        time_to_maturity = days_to_maturity / 365.0  # Act/365 convention
        return self.get_df(time_to_maturity)

    def __repr__(self):
        return f"DiscountCurve('{self.curve_name}', {len(self.tenors)} points)"


class ForwardCurve:
    '''
    Forward rate curve with linear interpolation.
    '''

    def __init__(
            self,
            curve_name: str,
            tenors: np.ndarray,
            forward_rates: np.ndarray
        ):
        self.curve_name = curve_name
        self.tenors = tenors                # Array of tenors in years
        self.forward_rates = forward_rates  # Corresponding forward rates

    def get_forward_rate(self, time_to_start: float) -> float:
        '''
        Get forward rate for a given time period.
        Uses linear interpolation between points.
        '''

        if time_to_start <= 0:
            return self.forward_rates[0]

        if time_to_start <= self.tenors[0]:
            return self.forward_rates[0]

        if time_to_start >= self.tenors[-1]:
            return self.forward_rates[-1]  # Flat extrapolation

        return np.interp(time_to_start, self.tenors, self.forward_rates)

    def __repr__(self):
        return f"ForwardCurve('{self.curve_name}', {len(self.tenors)} points)"


class MarketData:
    '''
    Market data container for a specific valuation date.
    Loads FX spot rates, discount curves, and forward curves from CSV files.
    '''

    def __init__(self, valuation_date: date):
        self.valuation_date = valuation_date
        self.fx_spots: Dict[Tuple[str, str], float] = {}    # {(ccy1, ccy2): rate}
        self.discount_curves: Dict[str, DiscountCurve] = {} # {curve_name: DiscountCurve}
        self.forward_curves: Dict[str, ForwardCurve] = {}   # {curve_name: ForwardCurve}


    def get_fx_spot(self, ccy1: str, ccy2: str) -> float:
        '''
        Get FX spot rate for currency pair.
        Handles both direct (USDRUB) and inverse (RUBUSD = 1/USDRUB).

        Raises:
            KeyError: If currency pair not found
        '''

        if (ccy1, ccy2) in self.fx_spots:
            return self.fx_spots[(ccy1, ccy2)]
        elif (ccy2, ccy1) in self.fx_spots:
            return 1.0 / self.fx_spots[(ccy2, ccy1)]
        else:
            raise KeyError(f"No FX spot rate found for {ccy1}/{ccy2} on {self.valuation_date}")


    @classmethod
    def load_from_csv(cls, valuation_date: date, data_path: str) -> 'MarketData':
        '''
        Load all market data from CSV files in data/market/ directory.
        '''

        market_data = cls(valuation_date)

        # Date format used: DD.MM.YYYY
        date_str = valuation_date.strftime('%d.%m.%Y')

        # FX spots
        market_data._load_fx_rates(f"{data_path}/usd_rates.csv", date_str, 'USD', 'RUB')
        market_data._load_fx_rates(f"{data_path}/eur_rates.csv", date_str, 'EUR', 'RUB')
        market_data._load_fx_rates(f"{data_path}/cny_rates.csv", date_str, 'CNY', 'RUB')

        # Discount curve
        market_data._load_discount_curves(f"{data_path}/discount_curves.csv", date_str)

        # Forward curves
        market_data._load_forward_curves(f"{data_path}/forward_curves.csv", date_str)

        return market_data


    def _load_fx_rates(self, filepath: str, date_str: str, ccy1: str, ccy2: str):
        '''
        Load FX rates. Format: nominal;data;curs;cdx
        '''

        try:
            df = pd.read_csv(filepath, sep=';', encoding='utf-8-sig')
            df_date = df[df['data'] == date_str]

            if not df_date.empty:
                # Convert comma to period for decimal separator
                rate_str = str(df_date.iloc[0]['curs']).replace(',', '.')
                rate = float(rate_str)

                # Store bidirectional
                self.fx_spots[(ccy1, ccy2)] = rate
                self.fx_spots[(ccy2, ccy1)] = 1.0 / rate
            else:
                print(f"Warning: No FX rate found for {ccy1}/{ccy2} on {date_str}")

        except FileNotFoundError:
            print(f"Warning: FX rates file not found: {filepath}")

        except Exception as e:
            print(f"Error loading FX rates from {filepath}: {e}")


    def _load_discount_curves(self, filepath: str, date_str: str):
        '''
        Load discount curves from file.
        '''

        try:
            df = pd.read_csv(filepath, encoding='utf-8-sig')
            df_date = df[df['Дата'] == date_str]

            if df_date.empty:
                print(f"Warning: No discount curves found for {date_str}")
                return

            # Group by curve name
            for curve_name, curve_data in df_date.groupby('Кривая'):
                # Extract currency from curve name
                parts = curve_name.split('-')

                if len(parts) >= 3 and parts[1] == 'DISCOUNT':
                    discount_ccy = parts[2]  # Discounting currency
                    curve_data = curve_data.sort_values('Тенор')

                    tenors = curve_data['Тенор'].values
                    dfs = curve_data['Ставка'].values

                    self.discount_curves[curve_name] = DiscountCurve(
                        curve_name=curve_name,
                        currency=discount_ccy,
                        tenors=tenors,
                        discount_factors=dfs
                    )

        except FileNotFoundError:
            print(f"Warning: Discount curves file not found: {filepath}")

        except Exception as e:
            print(f"Error loading discount curves: {e}")


    def _load_forward_curves(self, filepath: str, date_str: str):
        '''
        Load forward curves from file.
        '''

        try:
            df = pd.read_csv(filepath, encoding='utf-8-sig')
            df_date = df[df['Дата'] == date_str]

            if df_date.empty:
                print(f"Warning: No forward curves found for {date_str}")
                return

            # Group by curve name
            for curve_name, curve_data in df_date.groupby('Кривая'):
                curve_data = curve_data.sort_values('Тенор')

                tenors = curve_data['Тенор'].values
                rates = curve_data['Ставка'].values

                self.forward_curves[curve_name] = ForwardCurve(
                    curve_name=curve_name,
                    tenors=tenors,
                    forward_rates=rates
                )

        except FileNotFoundError:
            print(f"Warning: Forward curves file not found: {filepath}")

        except Exception as e:
            print(f"Error loading forward curves: {e}")


    def __repr__(self):
        return (f"MarketData({self.valuation_date}, "
                f"{len(self.fx_spots)} FX pairs, "
                f"{len(self.discount_curves)} discount curves, "
                f"{len(self.forward_curves)} forward curves)")
