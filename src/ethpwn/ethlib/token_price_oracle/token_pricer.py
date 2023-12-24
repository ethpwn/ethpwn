import datetime
import decimal
import sqlite3
import typing
import web3
import web3.types
from cachetools import LRUCache

from . import constants
from . import utils
from . import uniswap_v2_pricer
from . import uniswap_v3_pricer
from . import sushiswap_v2_pricer

import logging

l = logging.getLogger('token_price_oracle')

class TokenPricer:
    """
    Self-contained cache + oracle for token prices.
    """
    w3: web3.Web3
    cache: LRUCache

    def __init__(
            self,
            w3: web3.Web3,
            cache_size: int = 100_000
        ):
        self.w3 = w3
        self.cache = LRUCache(maxsize=cache_size)

    def price_token_dollars(
            self,
            token_address: str,
            block_identifier: web3.types.BlockIdentifier = 'latest',
            liveness_threshold_seconds: int = 60 * 60 * 24 * 7,
            decimals: typing.Optional[int] = None
        ) -> typing.Tuple[int, int]:
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
            token_address: the contract address of the token to price
            block_identifier: the block identifier for which we will get the price
            liveness_threshold_seconds: how many seconds of exchange inactivity may elapse before we disregard the exchange's price, default 7 days
            decimals: the number of decimals in the token, if known (otherwise it is looked up in the token contract)
        """
        this_cache_key = (token_address, block_identifier)
        if this_cache_key in self.cache:
            return self.cache[this_cache_key]

        if decimals is None:
            decimals = self.get_decimals(token_address)

        target_timestamp = datetime.datetime.fromtimestamp(self.get_block_timestamp(block_identifier), tz=datetime.timezone.utc)

        prices = []
        # Find all prices that tie this token to USD stablecoins directly
        for stablecoin, stablecoin_decimals in constants.STABLECOINS:
            this_token_prices = []
            try:
                k = (token_address, stablecoin, block_identifier, 'uniswap_v2_pricer')
                if k in self.cache:
                    report = self.cache[k]
                else:
                    report = uniswap_v2_pricer.price(self.w3, token_address, stablecoin, block_identifier)
                    self.cache[k] = report
                seconds_elapsed = (target_timestamp - report.timestamp).seconds
                if seconds_elapsed <= liveness_threshold_seconds:
                    this_token_prices.append((report.liquidity, report.price))
            except exceptions.ExchangeNotFound:
                pass

            try:
                k = (token_address, stablecoin, block_identifier, 'sushiswap_v2_pricer')
                if k in self.cache:
                    report = self.cache[k]
                else:
                    report = sushiswap_v2_pricer.price(self.w3, token_address, stablecoin, block_identifier)
                    self.cache[k] = report
                seconds_elapsed = (target_timestamp - report.timestamp).seconds
                if seconds_elapsed <= liveness_threshold_seconds:
                    this_token_prices.append((report.liquidity, report.price))
            except exceptions.ExchangeNotFound:
                pass

            for fee in [100, 500, 3_000, 10_000]:
                try:
                    k = (token_address, stablecoin, fee, block_identifier, 'uniswap_v3_pricer')
                    if k in self.cache:
                        report = self.cache[k]
                    else:
                        report = uniswap_v3_pricer.price(self.w3, token_address, stablecoin, fee, block_identifier)
                        self.cache[k] = report
                    seconds_elapsed = (target_timestamp - report.timestamp).seconds
                    if seconds_elapsed <= liveness_threshold_seconds:
                        this_token_prices.append((report.liquidity, report.price))
                except exceptions.ExchangeNotFound:
                    pass
            
            for liquidity, p in this_token_prices:
                adjustment_decimals = 18 - stablecoin_decimals
                this_price_dollars = p * (10 ** adjustment_decimals)
                this_liquidity = liquidity * (10 ** adjustment_decimals)
                prices.append((this_liquidity, this_price_dollars))

        # Find all prices that tie this token to WETH, and convert WETH to USD using the Chainlink price oracle
        dollars_per_eth = self.price_eth_dollars(block_identifier)

        try:
            report = uniswap_v2_pricer.price(self.w3, token_address, constants.WETH_ADDRESS, block_identifier)
            seconds_elapsed = (target_timestamp - report.timestamp).seconds
            if seconds_elapsed <= liveness_threshold_seconds:
                prices.append((int(report.liquidity * dollars_per_eth), report.price * dollars_per_eth))
        except exceptions.ExchangeNotFound:
            pass

        try:
            report = sushiswap_v2_pricer.price(self.w3, token_address, constants.WETH_ADDRESS, block_identifier)
            seconds_elapsed = (target_timestamp - report.timestamp).seconds
            if seconds_elapsed <= liveness_threshold_seconds:
                prices.append((int(report.liquidity * dollars_per_eth), report.price * dollars_per_eth))
        except exceptions.ExchangeNotFound:
            pass

        for fee in [100, 500, 3_000, 10_000]:
            try:
                report = uniswap_v3_pricer.price(self.w3, token_address, constants.WETH_ADDRESS, fee, block_identifier)
                seconds_elapsed = (target_timestamp - report.timestamp).seconds
                if seconds_elapsed <= liveness_threshold_seconds:
                    prices.append((int(report.liquidity * dollars_per_eth), report.price * dollars_per_eth))
            except exceptions.ExchangeNotFound:
                pass

        if len(prices) == 0:
            raise exceptions.NoPriceData(f'Could not find any fresh price feed for token {token_address}')

        ret = utils.weighted_median(prices)

        # adjust for decimals
        ret = ret / (10 ** (18 - decimals))

        self.cache[this_cache_key] = ret
        return ret


    def price_eth_dollars(self, block_identifier: web3.types.BlockIdentifier) -> decimal.Decimal:
        """
        Get the USD price of ETH.
        """
        k = (block_identifier, 'eth_dollars')
        if k in self.cache:
            return self.cache[k]
        else:
            l.debug(f'Fetching ETH price for {block_identifier}')
            retval = chainlink_eth_pricer.price_eth_dollars(
                self.w3,
                block_identifier
            )
            self.cache[k] = retval
            return retval

    def get_block_timestamp(self, block_identifier: web3.types.BlockIdentifier) -> int:
        """
        Get the timestamp of a block.
        """
        k = (block_identifier, 'timestamp')
        if k in self.cache:
            return self.cache[k]
        else:
            l.debug(f'Fetching block timestamp for {block_identifier}')
            retval = self.w3.eth.get_block(block_identifier)['timestamp']
            self.cache[k] = retval
            return retval

    def get_decimals(self, token_address: str) -> int:
        """
        Get the number of decimals in a token.
        """
        k = (token_address, 'decimals')
        if k in self.cache:
            return self.cache[k]
        else:
            l.debug(f'Fetching decimals for {token_address}')
            retval = self.w3.eth.call({
                'to': token_address,
                'data': '0x' + constants.DECIMALS_METHOD_SELECTOR.hex()
            })
            decimals = int.from_bytes(retval, 'big')
            self.cache[k] = decimals
            return decimals

