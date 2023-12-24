import datetime
import decimal
import statistics
import typing

import web3
import web3.contract

from . import constants
from . import exceptions
from . import structs
from . import utils


def price_eth_dollars(w3: web3.Web3, block_identifier: typing.Any, liveness_threshold_seconds = 60 * 60 * 24 * 7) -> decimal.Decimal:
    target_timestamp = utils.get_block_timestamp(w3, block_identifier)
    prices = []
    for token, decimals in constants.STABLECOINS:
        for fee in [100, 500, 3_000, 10_000]:
            try:
                report = price(w3, constants.WETH_ADDRESS, token, fee, block_identifier)

                seconds_elapsed = (target_timestamp - report.timestamp).seconds
                if seconds_elapsed > liveness_threshold_seconds:
                    continue

                adjustment_decimals = 18 - decimals
                this_price_dollars = report.price * (10 ** adjustment_decimals)
                prices.append((report.liquidity, this_price_dollars))
            except exceptions.ExchangeNotFound:
                pass

    return utils.weighted_median(prices)


def price(w3: web3.Web3, from_token: str, to_token: str, fee: int, block_identifier: typing.Any) -> structs.PriceReport:
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

    hexadem_ ='0xe34f199b19b2b4f47f68442619d555527d244f78a3297ea89325f843f87b8b54'
    factory = '0x1F98431c8aD98523631AE4a59f267346ea31F984' 
    abiEncoded_1 = utils.encode_abi(
        ['address', 'address', 'uint24'],
        (
            utils.to_checksum_address(token0),
            utils.to_checksum_address(token1),
            fee,
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

    bslot0 = w3.eth.get_storage_at(pair_address, '0x0', block_identifier=block_identifier).rjust(32, b'\x00')

    if len(bslot0.lstrip(b'\x00')) == 0:
        raise exceptions.ExchangeNotFound(f'Could not find exchange {pair_address} for pair {token0} {token1} fee {fee}')

    observation_index = int.from_bytes(bslot0[7:9], byteorder='big', signed=False)
    sqrt_price_ratio_x96 = int.from_bytes(bslot0[12:32], byteorder='big', signed=False)
    price = decimal.Decimal(sqrt_price_ratio_x96) / (1 << 96) * sqrt_price_ratio_x96 / (1 << 96)

    bslot = w3.eth.get_storage_at(pair_address, hex(0x8 + observation_index), block_identifier=block_identifier).rjust(32, b'\x00')
    block_ts = int.from_bytes(bslot[28:32], byteorder='big', signed=False)

    bliquidity = w3.eth.get_storage_at(pair_address, '0x4', block_identifier=block_identifier)
    bliquidity = bliquidity.rjust(32, b'\x00')
    liquidity = int.from_bytes(bliquidity[16:32], byteorder='big', signed=False)


    ts = datetime.datetime.fromtimestamp(block_ts, tz=datetime.timezone.utc)

    if zero_to_one:
        return structs.PriceReport(
            price     = price,
            liquidity = liquidity,
            timestamp = ts,
        )
    else:
        return structs.PriceReport(
            price     = decimal.Decimal(1) / price,
            liquidity = liquidity,
            timestamp = ts,
        )
