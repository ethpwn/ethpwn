
from hexbytes import HexBytes
import web3

from .utils import get_chain_name, get_chainid, to_snake_case
from .ethdbg_exceptions import InvalidTargetException

class TransactionDebugTarget:
    def __init__(self, w3) -> None:
        self.w3: web3.Web3 = w3

        self._defaults = {}

        self._target_address = None
        self._chain_name = None
        self._chain_id = None
        self._fork_name = None
        self._calldata = None
        self._block_number = None
        self._txid = None
        self._source_address = None
        self._source_private_key = None
        self._gas = None
        self._value = None
        self._sender = None
        self._origin = None
        self._gas_price = None
        self._max_fee_per_gas = None
        self._max_priority_fee_per_gas = None
        self._nonce = None
        self._tx_index = None

        self.debug_type = None

    def set_default(self, key, value):
        self._defaults[key] = value

    def set_defaults(self, **defaults):
        self._defaults.update(**defaults)

    def clear_defaults(self):
        self._defaults = {}

    @property
    def nonce(self):
        return self._nonce if self._nonce is not None else self._defaults.get('nonce', None)

    @nonce.setter
    def nonce(self, nonce):
        if nonce is not None:
            self._nonce = nonce

    @property
    def source_address(self):
        return self._source_address if self._source_address is not None else self._defaults.get('source_address', None)

    @source_address.setter
    def source_address(self, address):
        if address is not None:
            self._source_address = self.w3.to_checksum_address(address)

    @property
    def from_pk(self):
        return self._source_private_key if self._source_private_key is not None else self._defaults.get('from_pk', None)

    @from_pk.setter
    def from_pk(self, pk):
        if pk is not None:
            self._source_private_key = HexBytes(pk).hex()

    @property
    def target_address(self):
        return self._target_address if self._target_address is not None else self._defaults.get('target_address', None)

    @target_address.setter
    def target_address(self, address):
        if address is not None:
            self._target_address = self.w3.to_checksum_address(address)

    @property
    def calldata(self):
        return self._calldata if self._calldata is not None else self._defaults.get('calldata', None)

    @calldata.setter
    def calldata(self, calldata):
        if calldata is not None:
            self._calldata = HexBytes(calldata).hex()

    @property
    def chain(self):
        return self._chain_name

    @chain.setter
    def chain(self, chain=None):
        if chain is None:
            return

        self._chain_id = None
        self._chain_name = None

        if type(chain) is int:
            self.chain_id = chain
        elif type(chain) is str:
            self.chain_name = chain
        else:
            raise ValueError(f"Unknown chain type: {type(chain)} = {repr(chain)}")

    @property
    def chain_id(self):
        return self._chain_id

    @property
    def chain_name(self):
        return self._chain_name

    @chain_id.setter
    def chain_id(self, id):
        assert type(id) is int
        assert (self._chain_name is None) or (self._chain_name == get_chain_name(id))

        self._chain_id = id
        self._chain_name = get_chain_name(id)

    @chain_name.setter
    def chain_name(self, chain):
        assert type(chain) is str
        assert (self._chain_id is None) or (self._chain_id == get_chainid(chain))
        self._chain_name = chain
        self._chain_id = get_chainid(chain)

    @property
    def fork(self):
        return self._fork_name if self._fork_name is not None else self._defaults.get('fork', None)

    @fork.setter
    def fork(self, fork):
        assert self._fork_name is None or self._fork_name == fork
        if fork is not None:
            self._fork = fork

    @property
    def block_number(self):
        return self._block_number if self._block_number is not None else self._defaults.get('block_number', None)

    @block_number.setter
    def block_number(self, block_number):
        if block_number is not None:
            self._block_number = block_number
        return self

    @property
    def transaction_hash(self):
        return self._txid if self._txid is not None else self._defaults.get('transaction_hash', None)

    @transaction_hash.setter
    def transaction_hash(self, txid=None):
        assert self._txid is None or self._txid == txid
        if txid is not None:
            self._txid = txid

    @property
    def gas(self):
        return self._gas if self._gas is not None else self._defaults.get('gas', None)

    @gas.setter
    def gas(self, gas=None):
        #assert self._gas is None or self._gas == gas
        if gas is not None:
            self._gas = gas

    @property
    def value(self):
        return self._value if self._value is not None else self._defaults.get('value', None)

    @value.setter
    def value(self, value=None):
        if value is not None:
            self._value = value

    @property
    def sender(self):
        return self._sender if self._sender is not None else self._defaults.get('sender', None)

    @sender.setter
    def sender(self, sender=None):
        if sender is not None:
            self._sender = self.w3.to_checksum_address(sender)

    @property
    def origin(self):
        return self._origin if self._origin is not None else self._defaults.get('origin', None)

    @origin.setter
    def origin(self, origin=None):
        if origin is not None:
            self._origin = self.w3.to_checksum_address(origin)

    @property
    def gas_price(self):
        return self._gas_price if self._gas_price is not None else self._defaults.get('gas_price', None)

    @gas_price.setter
    def gas_price(self, gas_price=None):
        if gas_price is not None:
            self._gas_price = gas_price

    @property
    def max_fee_per_gas(self):
        return self._max_fee_per_gas if self._max_fee_per_gas is not None else self._defaults.get('max_fee_per_gas', None)

    @max_fee_per_gas.setter
    def max_fee_per_gas(self, max_fee_per_gas=None):
        if max_fee_per_gas is not None:
            self._max_fee_per_gas = max_fee_per_gas

    @property
    def max_priority_fee_per_gas(self):
        if self._max_priority_fee_per_gas is not None:
            return self._max_priority_fee_per_gas
        else:
            return self._defaults.get('max_priority_fee_per_gas', None)

    @max_priority_fee_per_gas.setter
    def max_priority_fee_per_gas(self, max_priority_fee_per_gas=None):
        if max_priority_fee_per_gas is not None:
            self._max_priority_fee_per_gas = max_priority_fee_per_gas

    def replay_transaction(self, txid, **kwargs) -> 'TransactionDebugTarget':
        assert txid is not None
        txid = HexBytes(txid).hex()

        tx_data = self.w3.eth.get_transaction(txid)

        self.transaction_hash = txid

        self.defaults = {
            'block_number': self.w3.eth.block_number,
            'chain_id': self.w3.eth.chain_id,
        }

        self.target_address = kwargs.pop('to', None) or tx_data.get('to', None)

        self.source_address = kwargs.pop('sender', None) or tx_data.get('from', None)
        self.calldata = kwargs.pop('calldata', None) or kwargs.pop('input', None) or tx_data.get('input', None)
        self.block_number = kwargs.pop('block_number', None) or self.w3.eth.block_number

        if type(self.block_number) == str:
            self.block_number = int(self.block_number, 10)

        for k, v in tx_data.items():
            k_snake = to_snake_case(k)
            value = kwargs.pop(k_snake, None) or kwargs.pop(k, None) or v
            try:
                setattr(self, k_snake, value)
            except AttributeError:
                pass

        for k, v in kwargs.items():
            if v is not None:
                setattr(self, k, v)

        self.debug_type = "replay"

        return self

    def new_transaction(self, to, calldata, wallet_conf, **kwargs):
        self.target_address = to
        self.calldata = calldata

        self.source_address = kwargs.pop('sender', None) or wallet_conf.address
        self.block_number = kwargs.pop('block_number', None) or  self.w3.eth.block_number

        if type(self.block_number) == str:
            self.block_number = int(self.block_number, 10)

        self.chain = kwargs.pop('chain', hex(self.w3.eth.chain_id))
        self.chain_id = self.w3.eth.chain_id

        for k, v in kwargs.items():
            if v is None:
                continue
            try:
                setattr(self, k, v)
            except AttributeError:
                pass
        self.debug_type = "new"
        return self


    def get_transaction_dict(self, **defaults):
        if self.chain_id is None:
            self.chain_id = self.w3.eth.chain_id
        assert self.source_address is not None
        assert self.nonce is not None

        txn: web3.types.TxParams = {
            'chainId':              self.chain_id,
            'data':                 HexBytes(self.calldata),
            'gas':                  self.gas,
            'gasPrice':             self.gas_price,
            'nonce':                self.nonce,
            'value':                self.value,
            'to':                   self.target_address
        }

        return txn