import datetime
import decimal
import typing

import web3

from . import constants
from . import structs 
from . import utils 
from . import exceptions

RESERVES_SLOT = '0x0000000000000000000000000000000000000000000000000000000000000008'

def price_eth_dollars(w3: web3.Web3, block_identifier: typing.Any, liveness_threshold_seconds = 60 * 60 * 24 * 7) -> decimal.Decimal:
    target_timestamp = utils.get_block_timestamp(w3, block_identifier)
    prices = []
    for token, decimals in constants.STABLECOINS:
        try:
            report = price(w3, constants.WETH_ADDRESS, token, block_identifier)

            seconds_elapsed = (target_timestamp - report.timestamp).seconds
            if seconds_elapsed > liveness_threshold_seconds:
                continue

            adjustment_decimals = 18 - decimals
            this_price_dollars = report.price * (10 ** adjustment_decimals)
            prices.append((report.liquidity, this_price_dollars))
        except exceptions.ExchangeNotFound:
            pass

    return utils.weighted_median(prices)


def price(w3: web3.Web3, from_token: str, to_token: str, block_identifier: typing.Any) -> structs.PriceReport:
    """
    Use Uniswap v2 to find the price of `from_token` in terms of `to_token`.
    """
    #
    # Compute pair address
    bfrom_token = bytes.fromhex(from_token[2:])
    bto_token = bytes.fromhex(to_token[2:])

    if bfrom_token < bto_token:
        zero_to_one = True
        token0 = bfrom_token
        token1 = bto_token
    else:
        zero_to_one = False
        token0 = bto_token
        token1 = bfrom_token

    hexadem_ ='0xe18a34eb0e04b04f7a0ac29a6e80748dca96319b42c54d679cb821dca90c6303'
    factory = '0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac'
    abiEncoded_1 = utils.encode_packed(
        ['address', 'address'],
        (
            utils.to_checksum_address(token0),
            utils.to_checksum_address(token1),
        )
    )
    salt_ = utils.solidity_keccak(['bytes'], ['0x' +abiEncoded_1.hex()])
    abiEncoded_2 = utils.encode_packed(
        [ 'address', 'bytes32'],
        (
            factory,
            salt_,
        ),
    )
    
    pair_address = utils.to_checksum_address(utils.solidity_keccak(['bytes','bytes'], ['0xff' + abiEncoded_2.hex(), hexadem_])[12:])

    #
    # query balances
    breserves = w3.eth.get_storage_at(pair_address, RESERVES_SLOT, block_identifier=block_identifier)

    if len(breserves.lstrip(b'\x00')) == 0:
        raise exceptions.ExchangeNotFound(f'Could not find exchange {pair_address} for pair {token0} {token1}')

    block_ts = int.from_bytes(breserves[0:4], byteorder='big', signed=False)
    reserve1 = int.from_bytes(breserves[4:18], byteorder='big', signed=False)
    reserve0 = int.from_bytes(breserves[18:32], byteorder='big', signed=False)

    ts = datetime.datetime.fromtimestamp(block_ts, tz=datetime.timezone.utc)

    if zero_to_one:
        return structs.PriceReport(
            price     = decimal.Decimal(reserve1) / decimal.Decimal(reserve0),
            liquidity = reserve0 * reserve1,
            timestamp = ts,
        )
    else:
        return structs.PriceReport(
            price     = decimal.Decimal(reserve0) / decimal.Decimal(reserve1),
            liquidity = reserve0 * reserve1,
            timestamp = ts,
        )
