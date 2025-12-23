from collections import defaultdict
from typing import Iterable, List

from domain.instruments  import Contract


class Portfolio:
    '''
    The container for the collection of contracts making up a portfolio.
    '''

    def __init__(
        self,
        contracts: Iterable,
        name: str | None = None,
        base_currency: str | None = None,
        metadata: dict | None = None,
    ):
        self.contracts = list(contracts)
        if not self.contracts:
            raise ValueError('Portfolio must not be empty.')

        self.name = name
        self.base_currency = base_currency
        self.metadata = metadata or dict()


    def __len__(self):
        return len(self.contracts)

    def __iter__(self):
        return iter(self.contracts)

    def __repr__(self):
        return f"Portfolio '{self.name}' ({len(self.contracts)} contracts)"
    
    def output(self) -> str:
        res = f'{self}:\n'
        for c in self.contracts:
            res += f'\t--> {c}\n'
        return res
    
    def set_name(self, name: str):
        try:
            self.name = str(name)
        except:
            raise ValueError('Portfolio name must be a string.')

    def get_by_type(self, products: tuple) -> List[Contract]:
        return [c for c in self.contracts if isinstance(c, products)]
