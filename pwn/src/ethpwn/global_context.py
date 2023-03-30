
import contextlib
import logging

from web3 import Web3, middleware
import web3
from web3.gas_strategies.rpc import rpc_gas_price_strategy
from web3.gas_strategies.time_based import fast_gas_price_strategy, construct_time_based_gas_price_strategy


class Web3Context:
    def __init__(self, w3=None, from_addr=None, private_key=None, log_level=logging.WARNING):
        self.w3 = w3

        self._default_from_addr = from_addr
        self._default_signing_key = private_key
        self.logger = logging.getLogger('Web3Context')
        self.logger.setLevel(log_level)

    @property
    def default_from_addr(self):
        from .config.wallets import get_wallet
        if self._default_from_addr is None:
            return get_wallet(None).address
        return self._default_from_addr

    @default_from_addr.setter
    def default_from_addr(self, value):
        self._default_from_addr = value

    @property
    def default_signing_key(self):
        from .config.wallets import get_wallet
        if self._default_signing_key is None:
            return get_wallet(None).private_key
        return self._default_signing_key

    @default_signing_key.setter
    def default_signing_key(self, value):
        self._default_signing_key = value

    # if the log_level is changed, update the logger
    @property
    def log_level(self):
        return logging.getLevelName(self.logger.level)

    @log_level.setter
    def log_level(self, value):
        self._log_level = value
        self.logger.setLevel(value)
        self._configure_logging()

    def connect_http(self, url):
        self.w3 = Web3(Web3.HTTPProvider(url))
        assert self.w3.is_connected()
        self._configure_w3()

    def connect_ipc(self, path='/home/eth/.ethereum/geth.ipc'):
        self.w3 = Web3(Web3.IPCProvider(path))
        assert self.w3.is_connected()
        self._configure_w3()

    def _configure_logging(self):
        logging.basicConfig()

    def _configure_w3(self):
        self.w3.eth.set_gas_price_strategy(
            construct_time_based_gas_price_strategy(
                60, # 1 minute
                sample_size=5,
                probability=80,
                weighted=True,
        ))

        self.w3.middleware_onion.add(middleware.time_based_cache_middleware)
        self.w3.middleware_onion.add(middleware.latest_block_based_cache_middleware)
        self.w3.middleware_onion.add(middleware.simple_cache_middleware)

    def pessimistic_gas_price_estimate(self):
        return context.w3.eth.generate_gas_price() * 2

    def pessimistic_transaction_cost(self, gas_used_estimate):
        return self.pessimistic_gas_price_estimate() * gas_used_estimate

context: Web3Context = Web3Context()

@contextlib.contextmanager
def with_local_context(**kwargs):
    global context
    old_context = context
    context = Web3Context(**kwargs)
    yield
    context = old_context