
import random
import copy
import argparse
import typing
import inspect
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
from cachetools import LRUCache
from eth_hash.auto import keccak
from eth_typing import Address, Hash32
from eth.vm.state import BaseState
from eth.vm.opcode import Opcode
from eth.vm.opcode_values import DIFFICULTY
from eth.abc import AccountDatabaseAPI, BlockHeaderAPI, DatabaseAPI, ComputationAPI, TransactionBuilderAPI, ChainContextAPI, ExecutionContextAPI, TransactionContextAPI, AtomicDatabaseAPI, StateAPI, OpcodeAPI, SignedTransactionAPI, ReceiptAPI
from eth.rlp.headers import BlockHeader
from eth.rlp.transactions import SignedTransactionMethods
from eth.constants import EMPTY_SHA3
from eth.rlp.sedes import *
from eth.db.chain import ChainDB
from eth.db.header import build_block_header
from eth.db.atomic import AtomicDB
from eth.vm.logic.invalid import InvalidOpcode
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
from ..ethlib.prelude import *

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
     'CREATE2',
     'CALL',
     'CALLCODE',
     'RETURN',
     'DELEGATECALL',
     'STATICCALL',
     'REVERT',
     'INVALID',
     'SELFDESTRUCT'
     ]


SetupHook = typing.Callable[[VM, SignedTransactionMethods], typing.Any]
FinishHook = typing.Callable[[VM, ReceiptAPI, ComputationAPI], typing.Any]
OpcodeHook = typing.Callable[[Opcode, ComputationAPI], typing.Any]
OpcodeExceptionHook = typing.Callable[[Opcode, ComputationAPI, Exception], typing.Any]

class AbstractCache:

    def get(self, key: bytes, default: bytes = None) -> bytes:
        ...

    def __getitem__(self, key: bytes) -> bytes:
        ...

    def __setitem__(self, key: bytes, value: bytes):
        ...


class LayeredCache(AbstractCache):
    layer_1: AbstractCache
    layer_2: AbstractCache

    def __init__(self, layer_1: AbstractCache, layer_2: typing.Optional[AbstractCache]) -> None:
        self.layer_1 = layer_1
        self.layer_2 = layer_2

    def get(self, key: bytes, default: bytes = None) -> bytes:
        ret = self.layer_1.get(key, default)
        if ret is None and self.layer_2 is not None:
            ret = self.layer_2.get(key, default)
        return ret

    def __getitem__(self, key: bytes) -> bytes:
        ret = self.layer_1.get(key, None)
        if ret is None:
            ret = self.layer_2[key]
        return ret

    def __setitem__(self, key: bytes, value: bytes):
        self.layer_1[key] = value
        if self.layer_2 is not None:
            self.layer_2[key] = value

class Analyzer:
    w3: web3.Web3
    block_number: int
    block_header: BlockHeaderAPI
    block: web3.types.BlockData
    next_txn_id: int
    vm: VM
    vm_old_handlers: dict = {}

    _user_cache: AbstractCache

    _pre_txn_setup_hooks: typing.List[typing.Tuple[int, SetupHook]]
    _post_txn_finish_hooks: typing.List[typing.Tuple[int, FinishHook]]
    _pre_opcode_hooks: typing.List[typing.Tuple[int, OpcodeHook]]
    _post_opcode_hooks: typing.List[typing.Tuple[int, OpcodeHook]]
    _opcode_exception_hooks: typing.List[typing.Tuple[int, OpcodeExceptionHook]]

    # used for caching block headers and contract code
    _cache = LRUCache(maxsize=1024)

    # records checkpoints as (id, transaction_index) tuples
    _checkpoints: typing.List[typing.Tuple[int, int]]

    def __init__(self) -> None:
        self._pre_txn_setup_hooks = []
        self._post_txn_finish_hooks = []
        self._pre_opcode_hooks = []
        self._post_opcode_hooks = []
        self._opcode_exception_hooks = []
        self._user_cache = None
        self._checkpoints = []

    def set_validation_enabled(self, validation_enabled: bool):
        """
        Set whether transaction validation is enabled (ie signature checking, ability to pay gas, etc)
        """
        type(self.vm).__validate_enabled = validation_enabled
        type(self.vm._state_class).__validate_enabled = validation_enabled

    def register_pre_txn_setup(self, priority: int, hook: SetupHook):
        """
        Register a setup hook to run before a transaction is applied.
        Hooks are run in priority-order, from least to greatest.
        """
        self._pre_txn_setup_hooks.append((priority, hook))
        self._pre_txn_setup_hooks = sorted(self._pre_txn_setup_hooks, key=lambda x: x[0])

    def register_post_txn_setup(self, priority: int, hook: FinishHook):
        """
        Register a cleanup hook to run after a transaction is applied.
        Hooks are run in priority-order, from least to greatest.
        """
        self._post_txn_finish_hooks.append((priority, hook))
        self._post_txn_finish_hooks = sorted(self._post_txn_finish_hooks, key=lambda x: x[0])

    def register_pre_opcode_hook(self, priority: int, hook: OpcodeHook):
        """
        Register a hook to run before an opcode is applied.
        Hooks are run in priority-order, from least to greatest.
        """
        self._pre_opcode_hooks.append((priority, hook))
        self._pre_opcode_hooks = sorted(self._pre_opcode_hooks, key=lambda x: x[0])

    def register_post_opcode_hook(self, priority: int, hook: OpcodeHook):
        """
        Register a hook to run after an opcode is applied.
        Hooks are run in priority-order, from least to greatest.
        """
        self._post_opcode_hooks.append((priority, hook))
        self._post_opcode_hooks = sorted(self._post_opcode_hooks, key=lambda x: x[0])

    def register_opcode_exception_hook(self, priority: int, hook: OpcodeExceptionHook):
        """
        Register a hook to run after an opcode throws an exception
        """
        self._opcode_exception_hooks.append((priority, hook))
        self._opcode_exception_hooks = sorted(self._opcode_exception_hooks, key=lambda x: x[0])

    def clear_hooks(self):
        """
        Clear all hooks
        """
        self._pre_txn_setup_hooks.clear()
        self._post_txn_finish_hooks.clear()
        self._pre_opcode_hooks.clear()
        self._post_opcode_hooks.clear()
        self._opcode_exception_hooks.clear()

    def checkpoint(self) -> int:
        checkpoint_id = self.vm.state._account_db.record()
        self._checkpoints.append((checkpoint_id, self.next_txn_id))
        return checkpoint_id

    def restore(self, checkpoint_id: int):
        """
        Restores state to a transaction given its checkpoint ID
        """
        for c, txn_idx in self._checkpoints:
            if c == checkpoint_id:
                break
        else:
            raise ValueError(f'No checkpoint id {checkpoint_id} exists')
        assert txn_idx <= self.next_txn_id, f'Cannot restore checkpoint into the future'

        self.next_txn_id = txn_idx

        # copied from AccountDB discard
        self.vm.state._account_db._journaldb.discard(checkpoint_id)
        self.vm.state._account_db._journaltrie.discard(checkpoint_id)
        # NOTE: this is not needed
        # self.vm.state._account_db._journal_accessed_state.discard(checkpoint)
        self.vm.state._account_db._account_cache.clear()
        for _, store in self.vm.state._account_db._dirty_account_stores():
            store.discard(checkpoint_id)


    @classmethod
    def from_block_number(
            cls,
            w3: web3.Web3,
            block_number: int,
            custom_cache: AbstractCache = None,
            infer_header: bool = False,
            hook = None
        ) -> 'Analyzer':
        """
        Construct an analyzer at the given block number.

        Args:
            w3: web3 connection
            block_number: the block number that this analyzer will execute as
            custom_cache: optional, a cache object
            infer_header: optional, whether to infer this block's header rather than load it
        """
        assert isinstance(w3, web3.Web3)
        assert isinstance(block_number, int)

        ret = Analyzer()
        ret.block_number = block_number
        ret.w3 = w3
        if not infer_header:
            ret.block = cls.get_block(w3, block_number)
        ret._user_cache = LayeredCache(cls._cache, custom_cache)
        ret.next_txn_id = 0

        ret.vm = ret._vm_at_block_start(w3, infer_header=infer_header, hook=hook)
        ret.block_header = ret.vm.get_header()

        return ret

    def advance_block(self):
        """
        Advance analyzer to the next block.
        MUST be called after all transactions are analyzed
        """
        assert self.next_txn_id == len(self.block['transactions'])

        self.next_txn_id = 0
        self.block_number = self.block_number + 1
        self.block_header = build_block_header(self.w3, self.block_number)
        self.block = self.get_block(self.w3, self.block_number)

        prev_vm = get_vm_for_block(self.block_number - 1)
        my_vm = get_vm_for_block(self.block_number)
        if prev_vm == my_vm:
            self.vm = self._vm_at_block_start(db=self.vm.chaindb)
        else:
            # fork -- get new db just in case
            print('processing fork... untested!!!')
            self.vm = self._vm_at_block_start()

    def next_transaction(self) -> typing.Optional[typing.Tuple[SignedTransactionMethods, ReceiptAPI, ComputationAPI]]:
        txn_idx = self.next_txn_id
        if txn_idx >= len(self.block['transactions']):
            return None
        self.next_txn_id += 1

        txn = build_transaction(self.vm, self.w3, self.block_number, txn_idx)

        receipt, computation = self.apply(txn)

        return txn, receipt, computation

    def apply(self, txn: SignedTransactionMethods) -> typing.Tuple[ReceiptAPI, ComputationAPI]:
        txn.check_signature_validity = lambda: None

        for _, hook in self._pre_txn_setup_hooks:
            hook(self.vm, txn)

        receipt, computation = self.vm.apply_transaction(
            header=self.vm.get_header(),
            transaction=txn,
        )

        for _, hook in self._post_txn_finish_hooks:
            hook(self.vm, receipt, computation)

        return receipt, computation

    def _hook(
            self,
            opcode: Opcode,
            computation: ComputationAPI = None
        ):
        """
        This hook runs on every opcode call and invokes each registered hook as appropriate
        """
        for _, hook in self._pre_opcode_hooks:
            hook(opcode, computation)

        try:
            opcode(computation=computation)
        except Exception as e:
            for _, hook in self._opcode_exception_hooks:
                hook(opcode, computation, e)
            raise e

        for _, hook in self._post_opcode_hooks:
            hook(opcode, computation)

    def _vm_at_block_start(
            self,
            web3: web3.Web3,
            infer_header = False,
            hook: typing.Callable[[Opcode, ComputationAPI], None] = None
        ) -> VM:
        # adb = AtomicDB(MemoryDB(self.w3, cache=self._user_cache))
        db = ChainDB(web3)

        # re-play state to construct the cache
        # get the right VM and construct it
        if hook == None:
            VMClass = get_vm_for_block(self.block_number, w3=self.w3, hook=self._hook)
        else:
            VMClass = get_vm_for_block(self.block_number, w3=self.w3, hook=hook)
        # pyevm updates the header's stateRoot as transactions execute -- we need to manually set it to the
        # stateRoot from the end of the prior block, since nothing executed yet
        old_block = self.get_block_header(
            self.w3,
            self.block_number - 1
        )

        if infer_header:
            # the header we need is not yet constructed since we're running on the tip ...
            # infer what the header would be
            built_header = old_block.copy(
                block_number = self.block_number,
                timestamp = old_block.timestamp + 13,
                parent_hash = old_block.hash
            )
        else:
            built_header = self.get_block_header(self.w3, self.block_number)

        state_root = old_block.state_root
        built_header = built_header.copy(gas_used = 0, state_root=state_root)

        if infer_header:
            block_identifier = old_block.hash
        else:
            block_identifier = self.block_number - 1

        vm = VMClass(
            web3              = web3,
            block_identifier  = block_identifier,
            header            = built_header,
            chain_context     = StubChainContext(),
            chaindb           = db,
            consensus_context = None,
        )

        return vm

    @classmethod
    def get_block_header(cls, w3: web3.Web3, block_number: int) -> BlockHeaderAPI:
        bblock_number = block_number.to_bytes(8, byteorder='big', signed=False)

        key = b'my_block_header_cache' + bblock_number
        if key in cls._cache:
            return cls._cache[key]

        header = build_block_header(w3, block_number)
        cls._cache[key] = header
        return header

    @classmethod
    def get_block(cls, w3: web3.Web3, block_number: int) -> web3.types.BlockData:
        bblock_number = block_number.to_bytes(8, byteorder='big', signed=False)

        key = b'my_block_cache' + bblock_number
        if key in cls._cache:
            return cls._cache[key]

        block = w3.eth.get_block(block_number)

        cls._cache[key] = block
        return block

    def hook_vm(self, hook: typing.Callable[[Opcode, ComputationAPI], None] = None):

        if hook is not None:
            # Extremely smart way to detect if stuff is already hooked, LOL.
            if "stub" in str(self.vm.state.computation_class.opcodes[0]):
                for i, opcode in sorted(self.vm.state.computation_class.opcodes.items()):
                    # Restore the old handlers
                    self.vm.state.computation_class.opcodes[i] = EVM_OLD_HANDLERS[i]

            # stub opcodes with a hook
            for i, opcode in sorted(self.vm.state.computation_class.opcodes.items()):
                assert 'stub' not in str(type(opcode))
                EVM_OLD_HANDLERS[i] = self.vm.state.computation_class.opcodes[i]

                # stupid: fix the fact that py-evm doesn't have a mnemonic set for SELFDESTRUCT
                # (because it is wrapped with a decorator)
                if hasattr(opcode, '__wrapped__'):
                    inner_func = inspect.unwrap(opcode)
                    mnemonic = inner_func.mnemonic
                    gas_cost = inner_func.gas_cost
                    opcode.mnemonic = mnemonic
                else:
                    mnemonic = opcode.mnemonic
                    gas_cost = opcode.gas_cost

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
                self.vm.state.computation_class.opcodes[i] = opcode_cls()

            # stub 'invalid opcode' with a hook
            if 'stub' not in str(self.vm.state.computation_class.invalid_opcode_class):
                old_cls = self.vm.state.computation_class.invalid_opcode_class

                def new_invalid_call(opcode: InvalidOpcode, **kwargs):
                    old_opcode = old_cls(opcode.value)

                    return hook(old_opcode, **kwargs)

                stub_cls = type(
                    'opcode:invalid:stub',
                    (self.vm.state.computation_class.invalid_opcode_class,),
                    {
                        '__call__': new_invalid_call
                    }
                )
                self.vm.state.computation_class.invalid_opcode_class = stub_cls


def build_transaction(vm: VM, w3: web3.Web3, block_number: int, transaction_index: int) -> SignedTransactionMethods:
    """
    Load a transaction from geth in the format pyevm likes (not json)
    """
    raw_txn = w3.eth.get_raw_transaction_by_block(block_number, transaction_index)
    return vm.get_transaction_builder().decode(raw_txn)


EVM_OLD_HANDLERS = {}
def get_vm_for_block(block_number: int, w3: web3.Web3 = None, hook: OpcodeHook = None) -> typing.Type[VM]:
    """
    Construct the approprate VM for the given block number, and optionally insert the given hook
    to run after each instruction.
    """
    global EVM_OLD_HANDLERS

    if w3.eth.chain_id == eth.chains.mainnet.constants.MAINNET_CHAIN_ID:

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
        elif block_number < eth.chains.mainnet.constants.PARIS_MAINNET_BLOCK:
            TargetVM = eth.vm.forks.gray_glacier.GrayGlacierVM
        elif block_number < 17034870:
            TargetVM = eth.vm.forks.paris.ParisVM
        else:
            TargetVM = eth.vm.forks.shanghai.ShanghaiVM

    elif w3.eth.chain_id == 11155111: # sepolia
        TargetVM = eth.vm.forks.shanghai.ShanghaiVM

    elif w3.eth.chain_id == 56: # binance
        TargetVM = eth.vm.forks.shanghai.ShanghaiVM

    if hook is None:
        return TargetVM

    TargetStateClass = TargetVM.get_state_class()

    class MyComputationClass(TargetStateClass.computation_class):
        opcodes: typing.Dict[int, OpcodeAPI] = TargetStateClass.computation_class.opcodes.copy()

    class MyStateClass(TargetStateClass):
        """only used to pass account db stub"""
        computation_class: typing.Type[ComputationAPI] = MyComputationClass
        __validate_enabled = False

        def validate_transaction(*args, **kwargs) -> None:
            if MyStateClass.__validate_enabled:
                super().validate_transaction(*args, **kwargs)

    class MyVM(TargetVM):
        """only used to pass account db stub (via MyStateClass)"""
        _state_class: typing.Type[BaseState] = MyStateClass
        __validate_enabled = False

        def validate_transaction_against_header(*args, **kwargs):
            if MyVM.__validate_enabled:
                super().validate_transaction_against_header(*args, **kwargs)

    if hook is not None:
        # Extremely smart way to detect if stuff is already hooked, LOL.
        if "stub" in str(MyStateClass.computation_class.opcodes[0]):
            for i, opcode in sorted(MyStateClass.computation_class.opcodes.items()):
                # Restore the old handlers
                MyStateClass.computation_class.opcodes[i] = EVM_OLD_HANDLERS[i]

        # stub opcodes with a hook
        for i, opcode in sorted(MyStateClass.computation_class.opcodes.items()):
            assert 'stub' not in str(type(opcode))
            EVM_OLD_HANDLERS[i] = MyStateClass.computation_class.opcodes[i]

            # stupid: fix the fact that py-evm doesn't have a mnemonic set for SELFDESTRUCT
            # (because it is wrapped with a decorator)
            if hasattr(opcode, '__wrapped__'):
                inner_func = inspect.unwrap(opcode)
                mnemonic = inner_func.mnemonic
                gas_cost = inner_func.gas_cost
                opcode.mnemonic = mnemonic
            else:
                mnemonic = opcode.mnemonic
                gas_cost = opcode.gas_cost

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

        # stub 'invalid opcode' with a hook
        if 'stub' not in str(MyStateClass.computation_class.invalid_opcode_class):
            old_cls = MyStateClass.computation_class.invalid_opcode_class

            def new_invalid_call(opcode: InvalidOpcode, **kwargs):
                old_opcode = old_cls(opcode.value)

                return hook(old_opcode, **kwargs)

            stub_cls = type(
                'opcode:invalid:stub',
                (MyStateClass.computation_class.invalid_opcode_class,),
                {
                    '__call__': new_invalid_call
                }
            )
            MyStateClass.computation_class.invalid_opcode_class = stub_cls

    return MyVM

# Stub classes that help plugging into pyevm
#
class StubChainContext:
    """only useful to specify chain id"""
    def __init__(self) -> None:
        self.chain_id = 1