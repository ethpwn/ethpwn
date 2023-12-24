import datetime
import decimal
import typing


class PriceReport(typing.NamedTuple):
    price: decimal.Decimal
    liquidity: int
    timestamp: datetime.datetime

