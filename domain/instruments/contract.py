from abc import ABC, abstractmethod
from datetime import date

from .directions import Direction


class Contract(ABC):

    def __init__(
        self,
        product: str,
        name: str,
        registration_date: date,
        maturity: int,
        start_date: date,
        end_date: date,
        direction: Direction,
        price: float | None,
    ):
        self.product = product
        self.name = name
        self.registration_date = registration_date
        self.maturity = maturity
        self.start_date = start_date
        self.end_date = end_date
        self.direction = direction
        self.price = price
