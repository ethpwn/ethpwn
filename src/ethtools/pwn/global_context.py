'''
Global context accessible from anywhere in the ethpwn package.
'''

import contextlib
import logging

from web3 import Web3, middleware
from web3.gas_strategies.time_based import construct_time_based_gas_price_strategy


class Web3Context:
    '''
    A context holding global state used by ethpwn.
    '''
    # pylint: disable=invalid-name
    def __init__(self, w3=None, from_addr=None, private_key=None, log_level=logging.WARNING, disable_autoconnect=False):
        self.w3 = w3

        self._default_from_addr = from_addr
        self._default_signing_key = private_key
        self.logger = logging.getLogger('Web3Context')
        self.logger.setLevel(log_level)

        if w3 is None:
            self.try_auto_connect()


    def try_auto_connect(self):
        '''
        Try to auto connect to a node if the default network is set and autoconnect is not disabled.
        '''
        if get_disable_autoconnect():
            return
        default_network = get_default_network()
        if default_network is not None:
            default_node_url = get_default_node_url_for_network(default_network)
            if default_node_url is not None:
                self.connect(default_node_url)


    @property
    def default_from_addr(self):
        '''
        Get the default from address as set or via the default wallet
        '''
        # pylint: disable=import-outside-toplevel
        from .config.wallets import get_wallet
        if self._default_from_addr is None:
            return get_wallet(None).address
        return self._default_from_addr

    @default_from_addr.setter
    def default_from_addr(self, value):
        self._default_from_addr = value

    @property
    def default_signing_key(self):
        '''
        Get the default signing key
        '''
        # pylint: disable=import-outside-toplevel
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
        '''
        Get the log level of the logger
        '''
        return logging.getLevelName(self.logger.level)

    @log_level.setter
    def log_level(self, value):
        self._log_level = value
        self.logger.setLevel(value)
        if not logging.getLogger().handlers:
            self.logger.addHandler(logging.StreamHandler())

    def connect(self, url, can_fail=False, **kwargs):
        '''
        Connect to the Ethereum node at `url` via HTTP/HTTPS, Websocket, or IPC depending on the URL scheme.
        If `can_fail` is True, then the function will return False if it fails to connect instead of raising an exception.
        '''
        if url.startswith('http'):
            return self.connect_http(url, can_fail=can_fail, **kwargs)
        elif url.startswith('ws'):
            return self.connect_websocket(url, can_fail=can_fail, **kwargs)
        else:
            return self.connect_ipc(url, can_fail=can_fail)

    def connect_http(self, url, can_fail=False, **kwargs):
        '''
        Connect to a remote Ethereum node via HTTP/HTTPS
        '''
        self.w3 = Web3(Web3.HTTPProvider(url, **kwargs))
        if not self.w3 or not self.w3.is_connected():
            if can_fail:
                self.logger.warning('Could not connect to %s', url)
                return False
            else:
                raise ValueError(f'Could not connect to {url}')
        else:
            self.logger.info('Connected to %s', url)
            self._configure_w3()
            return True

    def connect_ipc(self, path='/home/eth/.ethereum/geth.ipc', can_fail=False):
        '''
        Connect to a local Ethereum node via IPC
        '''
        self.w3 = Web3(Web3.IPCProvider(path))
        if not self.w3 or not self.w3.is_connected():
            if can_fail:
                self.logger.warning('Could not connect to %s', path)
                return False
            else:
                raise ValueError(f'Could not connect to {path}')
        else:
            self.logger.info('Connected to %s', path)
            self._configure_w3()
            return True

    def connect_websocket(self, url, can_fail=False, **kwargs):
        '''
        Connect to an Ethereum node via WebSockets
        '''
        self.w3 = Web3(Web3.WebsocketProvider(url, **kwargs))
        if not self.w3 or not self.w3.is_connected():
            if can_fail:
                self.logger.warning('Could not connect to %s', url)
                return False
            else:
                raise ValueError(f'Could not connect to {url}')
        else:
            self.logger.info('Connected to %s', url)
            self._configure_w3()
            return True

    def _configure_w3(self):
        '''
        Set up some reasonable defaults for gas estimation in the web3 context.
        '''
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
        '''
        Estimate the gas price for a transaction. This is a pessimistic estimate that will
        overestimate the gas price by a factor of 2. This should be good enough to mostly
        ensure that the transaction will be mined in a reasonable amount of time.
        '''
        return context.w3.eth.generate_gas_price() * 2

    def pessimistic_transaction_cost(self, gas_used_estimate):
        '''
        Estimate the cost of a transaction. This is a pessimistic estimate that will
        overestimate the gas price by a factor of 2. This should be good enough to mostly
        ensure that the transaction will be mined in a reasonable amount of time.
        '''
        return self.pessimistic_gas_price_estimate() * gas_used_estimate


from .config.misc import get_default_node_url_for_network, get_default_network, get_disable_autoconnect
context: Web3Context = Web3Context()

@contextlib.contextmanager
def with_local_context(**kwargs):
    '''
    Temporarily set the global context to a new context. Will restore the old context when the
    context manager exits.
    '''
    # pylint: disable=invalid-name,global-statement
    global context
    old_context = context
    context = Web3Context(**kwargs)
    yield
    context = old_context

