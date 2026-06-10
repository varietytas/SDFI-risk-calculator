from datetime import datetime

from domain.instruments import FxFwd, FxNdf, FxSwap, IRS, OIS
from domain.instruments import Direction


class InstrumentFactory:
    '''
    Converts the raw dict into an instance of the desired instrument type.
    '''

    def from_row(self, row: dict):
        product = row['product']

        if product == 'FX Fwd':
            return self._build_fx_fwd(row)
        if product == 'FX Ndf':
            return self._build_fx_ndf(row)
        if product == 'FX Swap':
            return self._build_fx_swap(row)
        if product == 'IRS':
            return self._build_irs(row)
        if product == 'OIS':
            return self._build_ois(row)

        raise ValueError(f'Unsupported product: {product}.')


    # ---------- FX FWD ----------

    def _clean_fx_fwd(self, row: dict) -> dict:
        '''Common cleaning and value parsing for FX Fwd rows.'''

        row = row.copy()

        to_drop = [
            'product',
            'margin',
            'order',
            'premium',
            'premium_date',
            'premium_currency',
            'strike'
        ]
        for feature in to_drop:
            row.pop(feature)

        row['name'] = self._parse_str(row.get('name'))
        row['registration_date'] = self._parse_date(row.get('registration_date'))

        row['start_date'] = self._parse_date(row.get('start_date'))
        row['end_date']   = self._parse_date(row.get('end_date'))
        row['maturity']   = (row['end_date'] - row['registration_date']).days

        row['direction']  = self._parse_direction(row.get('direction'))

        row['price']      = self._parse_float(row.get('price'))
        row['currency_1'] = self._parse_str(row.get('currency_1'))
        row['amount_1']   = self._parse_float(row.get('amount_1'))
        row['currency_2'] = self._parse_str(row.get('currency_2'))
        row['amount_2']   = self._parse_float(row.get('amount_2'))

        return row
  

    def _build_fx_fwd(self, row: dict) -> FxFwd:
        row = self._clean_fx_fwd(row)

        return FxFwd(
            name=row['name'],
            registration_date=row['registration_date'],
            maturity=row['maturity'],
            start_date=row['start_date'],
            end_date=row['end_date'],
            direction=row['direction'],
            price=row['price'],
            currency_1=row['currency_1'],
            amount_1=row['amount_1'],
            currency_2=row['currency_2'],
            amount_2=row['amount_2']
        )

    # ---------- FX NDF ----------

    def _build_fx_ndf(self, row: dict) -> FxNdf:
        row = self._clean_fx_fwd(row)

        return FxNdf(
            name=row['name'],
            registration_date=row['registration_date'],
            maturity=row['maturity'],
            start_date=row['start_date'],
            end_date=row['end_date'],
            direction=row['direction'],
            price=row['price'],
            currency_1=row['currency_1'],
            amount_1=row['amount_1'],
            currency_2=row['currency_2'],
            amount_2=row['amount_2']
        )

    # ---------- FX Swap ----------

    def _clean_fx_swap(self, row: dict) -> dict:
        '''Common cleaning and value parsing for FX Swap rows.'''

        row = row.copy()

        to_drop = [
            'product',
            'margin',
            'order',
            'premium',
            'premium_date',
            'premium_currency',
            'strike'
        ]
        for feature in to_drop:
            row.pop(feature)

        row['name'] = self._parse_str(row.get('name'))
        row['registration_date'] = self._parse_date(row.get('registration_date'))

        row['start_date'] = self._parse_date(row.get('start_date'))
        row['end_date']   = self._parse_date(row.get('end_date'))
        row['maturity']   = (row['end_date'] - row['start_date']).days

        row['direction']  = self._parse_direction(row.get('direction'))

        row['price']      = self._parse_float(row.get('price'))
        row['rate']       = self._parse_float(row.get('rate'))
        row['currency_1'] = self._parse_str(row.get('currency_1'))
        row['amount_1']   = self._parse_float(row.get('amount_1'))
        row['currency_2'] = self._parse_str(row.get('currency_2'))
        row['amount_2']   = self._parse_float(row.get('amount_2'))

        return row

    def _build_fx_swap(self, row: dict) -> FxSwap:
        row = self._clean_fx_swap(row)

        return FxSwap(
            name=row['name'],
            registration_date=row['registration_date'],
            maturity=row['maturity'],
            start_date=row['start_date'],
            end_date=row['end_date'],
            direction=row['direction'],
            price=row['price'],
            rate=row['rate'],
            currency_1=row['currency_1'],
            amount_1=row['amount_1'],
            currency_2=row['currency_2'],
            amount_2=row['amount_2']
        )

    # ---------- IRS ----------

    def _clean_irs(self, row: dict) -> dict:
        '''Common cleaning and value parsing for IRS rows.'''

        row = row.copy()

        to_drop = [
            'product',
            'currency_2',
            'amount_2',
            'margin',
            'order',
            'premium',
            'premium_date',
            'premium_currency',
            'strike'
        ]
        for feature in to_drop:
            row.pop(feature)

        row['name'] = self._parse_str(row.get('name'))
        row['registration_date'] = self._parse_date(row.get('registration_date'))

        row['start_date'] = self._parse_date(row.get('start_date'))
        row['end_date']   = self._parse_date(row.get('end_date'))
        row['maturity']   = (row['end_date'] - row['start_date']).days

        row['direction']  = self._parse_direction(row.get('direction'))

        row['price']      = self._parse_float(row.get('price'))
        row['currency_1'] = self._parse_str(row.get('currency_1'))
        row['amount_1']   = self._parse_float(row.get('amount_1'))

        row['index'] = ' '.join(row['name'].split()[2:])

        return row

    def _build_irs(self, row: dict) -> IRS:
        row = self._clean_irs(row)

        return IRS(
            name=row['name'],
            registration_date=row['registration_date'],
            maturity=row['maturity'],
            start_date=row['start_date'],
            end_date=row['end_date'],
            direction=row['direction'],
            price=row['price'],
            index=row['index'],
            currency=row['currency_1'],
            amount=row['amount_1'],
        )
    
    # ---------- OIS ----------

    def _build_ois(self, row: dict) -> OIS:
        row = self._clean_irs(row)

        return OIS(
            name=row['name'],
            registration_date=row['registration_date'],
            maturity=row['maturity'],
            start_date=row['start_date'],
            end_date=row['end_date'],
            direction=row['direction'],
            price=row['price'],
            index=row['index'],
            currency=row['currency_1'],
            amount=row['amount_1'],
        )

    # ---------- Parsing methods ----------

    @staticmethod
    def _parse_str(value):
        if value in (None, ''):
            return None
        return str(value)
    
    @staticmethod
    def _parse_int(value):
        if value in (None, ''):
            return None
        return int(value)

    @staticmethod
    def _parse_float(value: str):
        value = str(value)
        if value in (None, ''):
            return None
        return float(value.rstrip('% '))
    
    @staticmethod
    def _parse_date(value: str):
        value = str(value)
        if value in (None, ''):
            return None
        return datetime.strptime(value, "%d.%m.%Y").date()
    
    @staticmethod
    def _parse_direction(value):
        if value in (None, ''):
            return None
        try:
            return Direction(value)
        except:
            raise ValueError(f'Unknown direction: {value}.')
