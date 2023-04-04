
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

from eth_account import Account
import eth_account.signers.local

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
        validate_word(block_hash, title="Block Hash")
        try:
            bblock_number = db[b'H' + bytes(block_hash)]
            block_number = int.from_bytes(bblock_number, byteorder='big', signed=False)
            try:
                header_rlp = db[
                    b'h' +
                    int.to_bytes(block_number, length=8, signed=False, byteorder='big') +
                    bytes(block_hash)
                ]
            except KeyError:
                # might be in the freezer
                resp = provider.make_request('debug_dbAncient', ['headers', block_number])
                if 'result' in resp:
                    header_rlp = bytes.fromhex(resp['result'][2:])
                else:
                    raise
        except KeyError:
            raise HeaderNotFound(f"No header with hash {encode_hex(block_hash)} found")
        return _decode_block_header(header_rlp)

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
    """
    Load a block header from geth in the format pyevm likes (not json)
    """

    try:
        result = w3.provider.make_request('debug_getRawHeader', [hex(block_number)])
        b = bytes.fromhex(result['result'][2:])
        return _decode_block_header(b)
    except Exception:

        if w3.eth.chain_id == 11155111:
            block = w3.eth.get_block(block_number)
            BlockHeader = eth.vm.forks.paris.blocks.ParisBlockHeader

            block_kwargs = {}
            for key, value in block.items():
                key_snake = to_snake_case(key)
                if key_snake in BlockHeader._meta.field_names:
                    block_kwargs[key_snake] = value

            header = BlockHeader(
                block_number=block_number,
                **block_kwargs
            )
            return header
        else:
            raise


def get_vm_for_block(chain_id, block_number: int, hook: OpcodeHook = None) -> typing.Type[VM]:
    """
    Construct the approprate VM for the given block number, and optionally insert the given hook
    to run after each instruction.
    """

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
        called_set_balance = False

        def get_code(self, address: Address) -> bytes:
            validate_canonical_address(address, title="Storage Address")

            code_hash = self.get_code_hash(address)
            if code_hash == EMPTY_SHA3:
                return b''
            else:
                try:
                    return self._journaldb[b'c' + bytes(code_hash)]
                except KeyError:
                    raise MissingBytecode(code_hash) from KeyError
                finally:
                    if code_hash in self._get_accessed_node_hashes():
                        self._accessed_bytecodes.add(address)

        def set_code(self, address: Address, code: bytes) -> None:
            validate_canonical_address(address, title="Storage Address")
            validate_is_bytes(code, title="Code")

            account = self._get_account(address)

            code_hash = keccak(code)
            self._journaldb[b'c' + bytes(code_hash)] = code
            self._set_account(address, account.copy(code_hash=code_hash))

        def get_balance(self, address: Address) -> int:
            if not self.called_set_balance:
                return 10000000000000000000
            else:
                return super().get_balance(address)

        def set_balance(self, address: Address, balance: int) -> None:
            self.called_set_balance = True
            return super().set_balance(address, balance)

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
        # stub opcodes with a hook
        for i, opcode in sorted(MyStateClass.computation_class.opcodes.items()):
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