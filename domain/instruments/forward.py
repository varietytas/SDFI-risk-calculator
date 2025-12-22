from datetime import date

from .directions import Direction
from .contract import Contract


class FxFwd(Contract):
    
    def __init__(
        self,
        name: str,
        registration_date: date,
        maturity: int,
        start_date: date,
        end_date: date,
        direction: Direction,
        price: float,
        currency_1: str,
        amount_1: float,
        currency_2: str,
        amount_2: float,
    ):
        super().__init__(
            product='FX Fwd',
            name=name,
            registration_date=registration_date,
            maturity=maturity,
            start_date=start_date,
            end_date=end_date,
            direction=direction,
            price=price,
        )
        self.currency_1 = currency_1
        self.amount_1 = amount_1
        self.currency_2 = currency_2
        self.amount_2 = amount_2
    
    def __repr__(self):
        return f'{self.product} {self.maturity}D: {self.direction.value} {self.amount_1} {self.currency_1} for {self.amount_2} {self.currency_2} ({self.price} exchange rate) on {self.end_date}'


class FxNdf(Contract):
    
    def __init__(
        self,
        name: str,
        registration_date: date,
        maturity: int,
        start_date: date,
        end_date: date,
        direction: Direction,
        price: float,
        currency_1: str,
        amount_1: float,
        currency_2: str,
        amount_2: float,
    ):
        super().__init__(
            product='FX Ndf',
            name=name,
            registration_date=registration_date,
            maturity=maturity,
            start_date=start_date,
            end_date=end_date,
            direction=direction,
            price=price,
        )
        self.currency_1 = currency_1
        self.amount_1 = amount_1
        self.currency_2 = currency_2
        self.amount_2 = amount_2

    def __repr__(self):
        return f'{self.product} {self.maturity}D: {self.direction.value} {self.amount_1} {self.currency_1} for {self.amount_2} {self.currency_2} ({self.price} exchange rate) on {self.end_date}'
