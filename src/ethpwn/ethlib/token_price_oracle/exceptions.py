class ExchangeNotFound(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class NoPriceData(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
