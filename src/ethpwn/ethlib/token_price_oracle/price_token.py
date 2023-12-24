import datetime
import decimal
import statistics
import typing
import web3

from . import uniswap_v2_pricer
from . import uniswap_v3_pricer
from . import sushiswap_v2_pricer 
from . import chainlink_eth_pricer

from . import constants
from . import exceptions

from . import utils

def price_token_dollars(
        w3: web3.Web3,
        token_address: str,
        block_identifier: typing.Union[str, int],
        liveness_threshold_seconds: int = 60 * 60 * 24 * 7
    ) -> decimal.Decimal:
    """
    Get the price of a token in terms of dollars.

    Computes the price by taking the weighted median price of
    (1) all DeX exchanges that pair this token with a dollar stablecoin, and
    (2) all DeX exchanges that pair this token with WETH, which we convert to dollars using the
        Chainlink price oracle.
    where the weights are determined by available liquidity.

    NOTE: The price is accurate only if the number of decimals in the token is 18.
          To adjust, divide the price by power(10, 18 - decimals)

    Arguments:
        w3: web3 connection
        token_address: the contract address of the token to price
        block_identifier: the block identifier for which we will get the price
        liveness_threshold_seconds: how many seconds of exchange inactivity may elapse before we disregard the exchange's price, default 7 days
    """
    target_timestamp = utils.get_block_timestamp(w3, block_identifier)
    prices = []

    for stablecoin, decimals in constants.STABLECOINS:
        this_token_prices = []
        try:
            report = uniswap_v2_pricer.price(w3, token_address, stablecoin, block_identifier)
            seconds_elapsed = (target_timestamp - report.timestamp).seconds
            if seconds_elapsed <= liveness_threshold_seconds:
                this_token_prices.append((report.liquidity, report.price))
        except exceptions.ExchangeNotFound:
            pass

        try:
            report = sushiswap_v2_pricer.price(w3, token_address, stablecoin, block_identifier)
            seconds_elapsed = (target_timestamp - report.timestamp).seconds
            if seconds_elapsed <= liveness_threshold_seconds:
                this_token_prices.append((report.liquidity, report.price))
        except exceptions.ExchangeNotFound:
            pass

        for fee in [100, 500, 3_000, 10_000]:
            try:
                report = uniswap_v3_pricer.price(w3, token_address, stablecoin, fee, block_identifier)
                seconds_elapsed = (target_timestamp - report.timestamp).seconds
                if seconds_elapsed <= liveness_threshold_seconds:
                    this_token_prices.append((report.liquidity, report.price))
            except exceptions.ExchangeNotFound:
                pass
        
        for liquidity, p in this_token_prices:
            adjustment_decimals = 18 - decimals
            this_price_dollars = p * (10 ** adjustment_decimals)
            this_liquidity = liquidity * (10 ** adjustment_decimals)
            prices.append((this_liquidity, this_price_dollars))

    dollars_per_eth = chainlink_eth_pricer.price_eth_dollars(w3, block_identifier)

    try:
        report = uniswap_v2_pricer.price(w3, token_address, constants.WETH_ADDRESS, block_identifier)
        seconds_elapsed = (target_timestamp - report.timestamp).seconds
        if seconds_elapsed <= liveness_threshold_seconds:
            prices.append((int(report.liquidity * dollars_per_eth), report.price * dollars_per_eth))
    except exceptions.ExchangeNotFound:
        pass

    try:
        report = sushiswap_v2_pricer.price(w3, token_address, constants.WETH_ADDRESS, block_identifier)
        seconds_elapsed = (target_timestamp - report.timestamp).seconds
        if seconds_elapsed <= liveness_threshold_seconds:
            prices.append((int(report.liquidity * dollars_per_eth), report.price * dollars_per_eth))
    except exceptions.ExchangeNotFound:
        pass

    for fee in [100, 500, 3_000, 10_000]:
        try:
            report = uniswap_v3_pricer.price(w3, token_address, constants.WETH_ADDRESS, fee, block_identifier)
            seconds_elapsed = (target_timestamp - report.timestamp).seconds
            if seconds_elapsed <= liveness_threshold_seconds:
                prices.append((int(report.liquidity * dollars_per_eth), report.price * dollars_per_eth))
        except exceptions.ExchangeNotFound:
            pass

    if len(prices) == 0:
        raise exceptions.NoPriceData(f'Could not find any fresh price feed for token {token_address}')

    return utils.weighted_median(prices)


def price_token_eth(
        w3: web3.Web3,
        token_address: str,
        block_identifier: typing.Union[str, int],
        liveness_threshold_seconds: int = 60 * 60 * 24 * 7
    ) -> decimal.Decimal:
    """
    Get the price of a token in terms of ETH (returned in units of wei).

    Computes the price by taking the median price of all DeX exchanges that pair
    this token with ETH.

    NOTE: The price is accurate only if the number of decimals in the token is 18.
          To adjust, divide the price by power(10, 18 - decimals)

    Arguments:
        w3: web3 connection
        token_address: the contract address of the token to price
        block_identifier: the block identifier for which we will get the price
        liveness_threshold_seconds: how many seconds of exchange inactivity may elapse before we disregard the exchange's price, default 7 days
    """
    target_timestamp = utils.get_block_timestamp(w3, block_identifier)
    prices = []

    try:
        report = uniswap_v2_pricer.price(w3, token_address, constants.WETH_ADDRESS, block_identifier)
        seconds_elapsed = (target_timestamp - report.timestamp).seconds
        if seconds_elapsed <= liveness_threshold_seconds:
            prices.append((report.liquidity, report.price))
    except exceptions.ExchangeNotFound:
        pass

    try:
        report = sushiswap_v2_pricer.price(w3, token_address, constants.WETH_ADDRESS, block_identifier)
        seconds_elapsed = (target_timestamp - report.timestamp).seconds
        if seconds_elapsed <= liveness_threshold_seconds:
            prices.append((report.liquidity, report.price))
    except exceptions.ExchangeNotFound:
        pass

    for fee in [100, 500, 3_000, 10_000]:
        try:
            report = uniswap_v3_pricer.price(w3, token_address, constants.WETH_ADDRESS, fee, block_identifier)
            seconds_elapsed = (target_timestamp - report.timestamp).seconds
            if seconds_elapsed <= liveness_threshold_seconds:
                prices.append((report.liquidity, report.price))
        except exceptions.ExchangeNotFound:
            pass

    if len(prices) == 0:
        raise exceptions.NoPriceData(f'Could not find any fresh price feed for token {token_address}')

    return utils.weighted_median(prices)
