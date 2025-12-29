class Cash():

    def __init__(
            self,
            currency: str,
            rate: float = 0.0,
            maturity: int = -1
        ):
        self.currency = currency
        self.rate = rate
        self.maturity = maturity    # -1 by default means unlimited (# when rate = 0)

    def __repr__(self):
        return f'Cash position in {self.currency} under {self.rate}%'
