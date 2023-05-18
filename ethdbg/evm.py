
import random
import copy
import argparse
import typing
import os
import web3
import web3.types
import web3.exceptions
import eth.chains.mainnet.constants
from eth.exceptions import (
    HeaderNotFound,
)
from eth_utils import (
    encode_hex
)
from eth_hash.auto import keccak
from eth_typing import Address, Hash32
from eth.vm.state import BaseState
from eth.vm.opcode import Opcode
from eth.vm.opcode_values import DIFFICULTY
from eth.abc import AccountDatabaseAPI, BlockHeaderAPI, DatabaseAPI, ComputationAPI, TransactionBuilderAPI, ChainContextAPI, ExecutionContextAPI, TransactionContextAPI, AtomicDatabaseAPI, StateAPI, OpcodeAPI, SignedTransactionAPI
from eth.rlp.headers import BlockHeader
from eth.rlp.transactions import SignedTransactionMethods
from eth.constants import EMPTY_SHA3
from eth.rlp.sedes import *
from eth.db.chain import ChainDB
from eth.db.atomic import AtomicDB
from eth.db.header import _decode_block_header
from eth.validation import validate_canonical_address, validate_is_bytes, validate_word
from eth.vm.base import VM
from eth.vm.interrupt import (
    MissingBytecode,
)
from eth.db.backends.memory import MemoryDB
import eth.vm.forks
import eth.vm.forks.arrow_glacier
import eth.vm.forks.arrow_glacier.state
import eth.vm.forks.arrow_glacier.computation

# I guess this will be replaced by ShanghaiBlockHeader
from eth.vm.forks.paris.blocks import ParisBlockHeader

from eth_account import Account
import eth_account.signers.local
from ethpwn.prelude import *

OpcodeHook = typing.Callable[[Opcode, ComputationAPI], typing.Any]


CALL_OPCODES = ['CALL', 'CALLCODE', 'DELEGATECALL', 'STATICCALL', 'CREATE', 'CREATE2']
RETURN_OPCODES = ['RETURN', 'REVERT', 'STOP']

PRECOMPILED_CONTRACTS = {
    'ecRecover': 0x1,
    'SHA2-256': 0x2,
    'RIPEMD-160': 0x3,
    'identity': 0x4,
    'modexp': 0x5,
    'ecAdd': 0x6,
    'ecMul': 0x7,
    'ecPairing': 0x8,
    'blake2f': 0x9
}

ALL_EVM_OPCODES = [
     'STOP',
     'ADD',
     'MUL',
     'SUB',
     'DIV',
     'SDIV',
     'MOD',
     'SMOD',
     'ADDMOD',
     'MULMOD',
     'EXP',
     'SIGNEXTEND',
     'LT',
     'GT',
     'SLT',
     'SGT',
     'EQ',
     'NOT',
     'AND',
     'OR',
     'XOR',
     'BYTE',
     'SHL',
     'SHR',
     'SAR',
     'SHA3',
     'ADDRESS',
     'BALANCE',
     'ORIGIN',
     'CALLER',
     'CALLVALUE',
     'CALLDATALOAD',
     'CALLDATASIZE',
     'CALLDATACOPY',
     'CODESIZE',
     'CODECOPY',
     'GASPRICE',
     'EXTCODESIZE',
     'EXTCODECOPY',
     'RETURNDATASIZE',
     'RETURNDATACOPY',
     'BLOCKHASH',
     'COINBASE',
     'TIMESTAMP',
     'NUMBER',
     'DIFFICULTY',
     'GASLIMIT',
     'POP',
     'MLOAD',
     'MSTORE',
     'MSTORE8',
     'SLOAD',
     'SSTORE',
     'JUMP',
     'JUMPI',
     'PC',
     'MSIZE',
     'GAS',
     'JUMPDEST',
     'PUSH1',
     'PUSH2',
     'PUSH3',
     'PUSH4',
     'PUSH5',
     'PUSH6',
     'PUSH7',
     'PUSH8',
     'PUSH9',
     'PUSH10',
     'PUSH11',
     'PUSH12',
     'PUSH13',
     'PUSH14',
     'PUSH15',
     'PUSH16',
     'PUSH17',
     'PUSH18',
     'PUSH19',
     'PUSH20',
     'PUSH21',
     'PUSH22',
     'PUSH23',
     'PUSH24',
     'PUSH25',
     'PUSH26',
     'PUSH27',
     'PUSH28',
     'PUSH29',
     'PUSH30',
     'PUSH31',
     'PUSH32',
     'DUP1',
     'DUP2',
     'DUP3',
     'DUP4',
     'DUP5',
     'DUP6',
     'DUP7',
     'DUP8',
     'DUP9',
     'DUP10',
     'DUP11',
     'DUP12',
     'DUP13',
     'DUP14',
     'DUP15',
     'DUP16',
     'SWAP1',
     'SWAP2',
     'SWAP3',
     'SWAP4',
     'SWAP5',
     'SWAP6',
     'SWAP7',
     'SWAP8',
     'SWAP9',
     'SWAP10',
     'SWAP11',
     'SWAP12',
     'SWAP13',
     'SWAP14',
     'SWAP15',
     'SWAP16',
     'LOG0',
     'LOG1',
     'LOG2',
     'LOG3',
     'LOG4',
     'CREATE',
     'CALL',
     'CALLCODE',
     'RETURN',
     'DELEGATECALL',
     'STATICCALL',
     'REVERT',
     'INVALID',
     'SELFDESTRUCT'
     ]

def get_w3_provider():
    web3_host = 'ws://128.111.49.122:8546'
    if web3_host.startswith('http'):
        context.connect_http(
            web3_host
        )
    elif web3_host.startswith('ws'):
        context.connect_websocket(
            web3_host,
            websocket_timeout=60 * 5,
            websocket_kwargs={
                'max_size': 1024 * 1024 * 1024,
            },
        )
    else:
        raise Exception("Unknown web3 provider")

    w3 = context.w3
    assert w3.is_connected()
    return w3


# STUBS
# ============================
class StubChainContext:
    """only useful to specify chain id"""

    def __init__(self) -> None:
        self.chain_id = 1

class StubMemoryDB(MemoryDB):
    """
    in-memory database that loads from geth as a fallback

    expects access to global 'provider'
    """

    def __init__(
            self,
            w3: web3.Web3,
            kv_store: typing.Dict[bytes, bytes] = None
        ) -> None:
        self._w3 = w3
        super().__init__(kv_store)

    def __getitem__(self, key: bytes) -> bytes:
        if not super()._exists(key):
            # TODO this will be gone, we will stub it in MyAccountDb
            assert(False)
            got = self._w3.provider.make_request('debug_dbGet', ['0x' + bytes(key).hex()])
            b = bytes.fromhex(got['result'][2:])
            super().__setitem__(key=key, value=b)
        return super().__getitem__(key)

    def __setitem__(self, key: bytes, value: bytes) -> None:
        self.kv_store[key] = value

    def _exists(self, key: bytes) -> bool:
        return key in self.kv_store

    def __delitem__(self, key: bytes) -> None:
        del self.kv_store[key]

    def __iter__(self) -> typing.Iterator[bytes]:
        return iter(self.kv_store)

    def __len__(self) -> int:
        return len(self.kv_store)

    def __repr__(self) -> str:
        return f"MemoryDB({self.kv_store!r})"

class MyChainDB(ChainDB):
    """
    Stub blockchain db that adds awareness of geth's storage scheme
    """

    @staticmethod
    def _get_block_header_by_hash(db: DatabaseAPI, block_hash: Hash32) -> BlockHeaderAPI:
        """
        Returns the requested block header as specified by block hash.

        Raises BlockNotFound if it is not present in the db.
        """
        w3 = get_w3_provider()
        block = w3.eth.get_block(block_hash)
        decoded_block_header = ParisBlockHeader(
            difficulty       = 0,
            block_number     = block['number'],
            gas_limit        = block['gasLimit'],
            timestamp        = block['timestamp'],
            coinbase         = bytes.fromhex(block['miner'][2:]),
            parent_hash      = bytes(block['parentHash']),
            # uncles_hash      = bytes(block.block['uncles']), # NOTE: excluded because web3py give us the wrong type (list vs hash)
            state_root       = bytes(block['stateRoot']),
            transaction_root = bytes(block['transactionsRoot']),
            receipt_root     = bytes(block['receiptsRoot']),
            bloom            = int.from_bytes(block['logsBloom'], byteorder='big', signed=False),
            gas_used         = int(block['gasUsed']),
            extra_data       = bytes(block['extraData']),
            mix_hash         = bytes(block['mixHash']),
            nonce            = bytes(block['nonce']),
            base_fee_per_gas = int(block.get('baseFeePerGas'), 0)
        )

        return decoded_block_header

# ============================

# SUPPORT FOR PARIS COMPUTATION
# =============================
PREVRANDAO = DIFFICULTY

PARIS_OPCODES = copy.deepcopy(eth.vm.forks.arrow_glacier.computation.ArrowGlacierComputation.opcodes)

def prevrandao(computation: ComputationAPI) -> None:
    computation.stack_push_int(computation.state.execution_context.prevrandao)

PARIS_OPCODES[PREVRANDAO] = Opcode.as_opcode(
    gas_cost=PARIS_OPCODES[DIFFICULTY].gas_cost,
    mnemonic='PREVRANDAO',
    logic_fn=prevrandao
)

class ParisComputation(eth.vm.forks.arrow_glacier.computation.ArrowGlacierComputation):
    opcodes: typing.Dict[int, OpcodeAPI] = PARIS_OPCODES

class ParisState(eth.vm.forks.arrow_glacier.state.ArrowGlacierState):
    computation_class: typing.Type[ComputationAPI] = ParisComputation

class ParisVM(eth.vm.forks.arrow_glacier.ArrowGlacierVM):
    """
    VM for Paris hardfork
    """
    # fork name
    fork = 'paris'

    _state_class: typing.Type[BaseState] = ParisState

    @classmethod
    def create_execution_context(
            cls,
            header: BlockHeaderAPI,
            prev_hashes: typing.Iterable[Hash32],
            chain_context: ChainContextAPI) -> ExecutionContextAPI:
        ret = super().create_execution_context(header, prev_hashes, chain_context)
        ret.prevrandao = int.from_bytes(header.mix_hash, byteorder='big', signed=False)
        return ret
# =============================

# BUILD STUFF
# ===========

def to_snake_case(s: str) -> str:
    s = s.replace('-', '_')
    return ''.join(['_' + c.lower() if c.isupper() else c for c in s]).lstrip('_')

def build_block_header(w3: web3.Web3, block_number: int) -> BlockHeader:

    block = w3.eth.get_block(block_number)

    # TODO Given a vm we should fetch the righ block header class
    decoded_block_header = ParisBlockHeader(
        difficulty       = 0,
        block_number     = block['number'],
        gas_limit        = block['gasLimit'],
        timestamp        = block['timestamp'],
        coinbase         = bytes.fromhex(block['miner'][2:]),
        parent_hash      = bytes(block['parentHash']),
        # uncles_hash      = bytes(block.block['uncles']), # NOTE: excluded because web3py give us the wrong type (list vs hash)
        state_root       = bytes(block['stateRoot']),
        transaction_root = bytes(block['transactionsRoot']),
        receipt_root     = bytes(block['receiptsRoot']),
        bloom            = int.from_bytes(block['logsBloom'], byteorder='big', signed=False),
        gas_used         = int(block['gasUsed']),
        extra_data       = bytes(block['extraData']),
        mix_hash         = bytes(block['mixHash']),
        nonce            = bytes(block['nonce']),
        base_fee_per_gas = int(block.get('baseFeePerGas', 0))
    )

    return decoded_block_header


EVM_OLD_HANDLERS = {}
def get_vm_for_block(chain_id, block_number: int, hook: OpcodeHook = None) -> typing.Type[VM]:
    """
    Construct the approprate VM for the given block number, and optionally insert the given hook
    to run after each instruction.
    """
    global OLD_HANDLER

    if chain_id == eth.chains.mainnet.constants.MAINNET_CHAIN_ID:

        assert block_number >= eth.chains.mainnet.constants.PETERSBURG_MAINNET_BLOCK

        if block_number < eth.chains.mainnet.constants.ISTANBUL_MAINNET_BLOCK:
            TargetVM = eth.vm.forks.petersburg.PetersburgVM
        elif block_number < eth.chains.mainnet.constants.MUIR_GLACIER_MAINNET_BLOCK:
            TargetVM = eth.vm.forks.istanbul.IstanbulVM
        elif block_number < eth.chains.mainnet.constants.BERLIN_MAINNET_BLOCK:
            TargetVM = eth.vm.forks.muir_glacier.MuirGlacierVM
        elif block_number < eth.chains.mainnet.constants.LONDON_MAINNET_BLOCK:
            TargetVM = eth.vm.forks.berlin.BerlinVM
        elif block_number < eth.chains.mainnet.constants.ARROW_GLACIER_MAINNET_BLOCK:
            TargetVM = eth.vm.forks.london.LondonVM
        elif block_number < eth.chains.mainnet.constants.GRAY_GLACIER_MAINNET_BLOCK:
            TargetVM = eth.vm.forks.arrow_glacier.ArrowGlacierVM
        elif block_number < 15537394:
            TargetVM = eth.vm.forks.gray_glacier.GrayGlacierVM
        else:
            TargetVM = ParisVM

    elif chain_id == 11155111: # sepolia
        TargetVM = ParisVM

    TargetStateClass = TargetVM.get_state_class()
    TargetAccountDBClass = TargetStateClass.get_account_db_class()

    class MyAccountDb(TargetAccountDBClass):
        """
        Stub account db that adds awareness of geth's storage pattern

        most code copy+pasted from pyevm
        """
        _w3 = get_w3_provider()
        called_set_balance = False

        storage_cache = {}
        balance_cache = {}
        nonce_cache = {}
        code_cache = {}

        def _get_account(self, address):
            from eth.rlp.accounts import Account
            #print(f"Asking for {address.hex()}")
            #import ipdb; ipdb.set_trace()
            nonce = self._w3.eth.get_transaction_count(address, block_number)
            balance = self._w3.eth.get_balance(address, block_number)
            account = Account(nonce=nonce, balance=balance)
            return account

        def account_exists(self, address):
            return True

        def get_storage(self, address: Address, slot: int, from_journal: bool = True) -> int:
            addr = address.hex()
            if addr not in self.storage_cache.keys():
                self.storage_cache[addr] = {}
                self.storage_cache[addr][slot] = None

                data = int.from_bytes(self._w3.eth.get_storage_at(address, slot, block_identifier=block_number), byteorder='big')
                #print(f'Got storage for {address.hex()} at slot {slot}, value {hex(data)} (web3) block {block_number}')
                self.storage_cache[addr][slot] = data

            elif slot not in self.storage_cache[addr].keys():
                self.storage_cache[addr][slot] = None
                data = int.from_bytes(self._w3.eth.get_storage_at(address, slot, block_identifier=block_number), byteorder='big')
                #print(f'Got storage for {address.hex()} at slot {slot}, value {hex(data)} (web3) block {block_number}')
                self.storage_cache[addr][slot] = data
            else:
                data = self.storage_cache[addr][slot]
                #print(f'Got storage for {address.hex()} at slot {slot}, value {hex(data)} (cache)')

            return data

        def set_storage(self, address: Address, slot: int, value: int) -> None:
            #print(f'Setting storage for {address.hex()} at slot {slot}, value {value}')
            addr = address.hex()
            if addr not in self.storage_cache.keys():
                self.storage_cache[addr] = {}
                self.storage_cache[addr][slot] = value
            else:
                self.storage_cache[addr][slot] = value

        def get_nonce(self, address):
            addr = address.hex()
            if addr not in self.nonce_cache.keys():
                self.nonce_cache[addr] = self._w3.eth.get_transaction_count(address, block_number)
            return self.nonce_cache[addr]

        def set_nonce(self, address: Address, nonce: int) -> None:
            addr = address.hex()
            self.nonce_cache[addr] = nonce

        def get_code(self, address: Address) -> bytes:
            validate_canonical_address(address, title="Storage Address")
            return self._w3.eth.get_code(address, block_number)

        def increment_nonce(self, address: Address) -> None:
            current_nonce = self.get_nonce(address)
            self.set_nonce(address, current_nonce + 1)

        def get_balance(self, address: Address) -> int:
            addr = address.hex()
            if addr not in self.balance_cache.keys():
                self.balance_cache[addr] = self._w3.eth.get_balance(address, block_number)
            return self.balance_cache[addr]

        def set_balance(self, address: Address, balance: int) -> None:
            addr = address.hex()
            self.balance_cache[addr] = balance

    class MyStateClass(TargetStateClass):
        """only used to pass account db stub"""
        account_db_class: typing.Type[AccountDatabaseAPI] = MyAccountDb

        # Stub this if you want to skip signature verification.
        def validate_transaction(
            self,
            transaction: SignedTransactionAPI):
            return True

    class MyVM(TargetVM):
        """only used to pass account db stub (via MyStateClass)"""
        _state_class: typing.Type[BaseState] = MyStateClass

        def validate_transaction_against_header(*args, **kwargs):
            # Never check for gasPrice.
            pass


    if hook is not None:
        # Extremely smart way to detect if stuff is already hooked, LOL.
        if "stub" in str(MyStateClass.computation_class.opcodes[0]):
            for i, opcode in sorted(MyStateClass.computation_class.opcodes.items()):
                # Restore the old handlers
                MyStateClass.computation_class.opcodes[i] = EVM_OLD_HANDLERS[i]

        # stub opcodes with a hook
        for i, opcode in sorted(MyStateClass.computation_class.opcodes.items()):

            EVM_OLD_HANDLERS[i] = MyStateClass.computation_class.opcodes[i]

            def new_call(opcode=opcode, **kwargs): # use opcode=opcode to ensure it's bound to the func
                return hook(opcode, **kwargs)

            # copy+pasted from pyevm opcode.py
            props = {
                '__call__': staticmethod(new_call),
                'mnemonic': opcode.mnemonic,
                'gas_cost': opcode.gas_cost,
            }
            opcode_cls = type(f"opcode:{opcode.mnemonic}:stub", (Opcode,), props)

            # override opcode with our hooked one
            MyStateClass.computation_class.opcodes[i] = opcode_cls()

    return MyVM