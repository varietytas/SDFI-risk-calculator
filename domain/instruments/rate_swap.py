from datetime import date

from .directions import Direction
from .contract import Contract


class IRS(Contract):

    def __init__(
        self,
        name: str,
        registration_date: date,
        maturity: int,
        start_date: date,
        end_date: date,
        direction: Direction,
        price: float,   # Fixed stream
        index: str,     # Floating stream
        currency: str,
        amount: float,
    ):
        super().__init__(
            product='IRS',
            name=name,
            registration_date=registration_date,
            maturity=maturity,
            start_date=start_date,
            end_date=end_date,
            direction=direction,
            price=price,
        )
        self.index = index
        self.currency = currency
        self.amount = amount
    
    def __repr__(self):
        return f'{self.product} {self.maturity}D: {self.direction.value} {self.price * 100}% for {self.index} on {self.amount} {self.currency} from {self.start_date} to {self.end_date}'


class OIS(Contract):

    def __init__(
        self,
        name: str,
        registration_date: date,
        maturity: int,
        start_date: date,
        end_date: date,
        direction: Direction,
        price: float,   # Fixed stream
        index: str,   # Floating stream
        currency: str,
        amount: float,
    ):
        super().__init__(
            product='OIS',
            name=name,
            registration_date=registration_date,
            maturity=maturity,
            start_date=start_date,
            end_date=end_date,
            direction=direction,
            price=price,
        )
        self.index = index
        self.currency = currency
        self.amount = amount
    
    def __repr__(self):
        return f'{self.product} {self.maturity}D: {self.direction.value} {self.price * 100}% for {self.index} on {self.amount} {self.currency} from {self.start_date} to {self.end_date}'
