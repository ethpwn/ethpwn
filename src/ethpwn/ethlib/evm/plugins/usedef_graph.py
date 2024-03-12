"""
This module contains the functions to generate the use-def graph of a given
transaction execution.
"""

import logging
import collections
import typing

import web3
import networkx as nx

from .base import *
from .call_tracer import CallTracer
from .utils import read_stack_int, read_stack_bytes, calculate_create_contract_address, calculate_create2_contract_address

l = logging.getLogger(__name__)

#
# Node types
#

# Data sources
PUSH = 'push'
ORIGIN = 'origin'
CALLER = 'caller'
ADDRESS = 'address'
CALLVALUE = 'callvalue'
CALLDATASIZE = 'calldatasize'
CALLDATA = 'calldata'
CALLDATALOAD = 'calldataload'
CALLDATACOPY = 'calldatacopy'
CODESIZE = 'codesize'
CODECOPY = 'codecopy'
EXTCODESIZE = 'extcodesize'
EXTCODEHASH = 'extcodehash'
EXTCODECOPY = 'extcodecopy'
CODE = 'code'
GASPRICE = 'gasprice'
COINBASE = 'coinbase'
TIMESTAMP = 'timestamp'
NUMBER = 'number'
DIFFICULTY = 'difficulty'
GASLIMIT = 'gaslimit'
CHAINID = 'chainid'
BALANCE = 'balance'
SELFBALANCE = 'selfbalance'
BASEFEE = 'basefee'
RETURNDATASIZE = 'returndatasize'
GAS = 'gas'
PC = 'pc'
GASPRICE = 'gasprice'
DUP = 'dup'
BLOCKHASH = 'blockhash'
MSIZE = 'msize'
PREVRANDAO = 'prevrandao'

#ops
BYTE = 'byte'
AND = 'and'
OR = 'or'
XOR = 'xor'
EQ = 'eq'
SHR = 'shr'
LT = 'lt'
GT = 'gt'
SLT = 'slt'
SGT = 'sgt'
ADD = 'add'
SUB = 'sub'
MUL = 'mul'
MULMOD = 'mulmod'
DIV = 'div'
SHL = 'shl'
SHR = 'shr'
EXP = 'exp'
ISZERO = 'iszero'
NOT = 'not'
MOD = 'mod'
SMOD = 'smod'
SDIV = 'sdiv'
SAR = 'sar'
ADDMOD = 'addmod'

# memory
MSTORE = 'mstore'
MSTORE8 = 'mstore8'
MLOAD = 'mload'
# occurs when we overwrite a memory location
MSTORE_TRUNCATION = 'mstore_truncation'

# storage
EXISTING_STORAGE = 'existing_storage'
SSTORE = 'sstore'
SLOAD = 'sload'

SHA3 = 'sha3'

LOG = 'log'

# Control flow
JUMP = 'jump'
JUMPI = 'jumpi'
REVERT = 'revert'

# Calls
CALL = 'call'
STATICCALL = 'staticcall'
DELEGATECALL = 'delegatecall'
CREATE = 'create'
CREATE2 = 'create2'

RETURN = 'return'
RETURNDATACOPY = 'returndatacopy'

SIGNEXTEND = 'signextend'

# Other
SELFDESTRUCT = 'selfdestruct'
INVALID = 'invalid'

class UseDefGraph(BaseAnalysisPlugin):

    name = "usedef_graph"

    PRE_OPERATION_PRIORITY: int = 50

    g: nx.MultiDiGraph
    next_id: int
    call_tracer: CallTracer

    _shadow_stacks: typing.Dict[int, typing.List[int]]
    _shadow_memory: typing.Dict[int, typing.List['_MemoryItem']]
    _shadow_returndata: typing.Dict[int, '_ReturndataItem']
    _shadow_call_details: typing.Dict[int, '_CallContext']
    _shadow_storage: typing.Dict[int, typing.Dict[int, '_StorageItem']]

    def __init__(self, call_tracer: CallTracer) -> None:
        self.next_id = 1
        self.call_tracer = call_tracer

    def pre_transaction_hook(self, vm: VM, txn: SignedTransactionMethods):
        self.g = nx.MultiDiGraph()
        self._shadow_stacks = {}
        self._shadow_memory = {}
        self._shadow_returndata = {}
        self._shadow_storage = collections.defaultdict(dict)
        self._shadow_call_details = {}

        # root-level context
        self.g.add_node(
            'NUMBER',
            type=NUMBER,
            value=vm.state.block_number,
        )
        self.g.add_node(
            'ORIGIN',
            type=ORIGIN,
            value=txn.sender,
        )
        self.g.add_node(
            'TIMESTAMP',
            type=TIMESTAMP,
            value=vm.get_header().timestamp,
        )
        self.g.add_node(
            'COINBASE',
            type=COINBASE,
            value=vm.get_header().coinbase,
        )
        self.g.add_node(
            'DIFFICULTY',
            type=DIFFICULTY,
            value=vm.get_header().difficulty,
        )
        self.g.add_node(
            'GASLIMIT',
            type=GASLIMIT,
            value=vm.get_header().gas_limit,
        )
        self.g.add_node(
            'CHAINID',
            type=CHAINID,
            value=vm.chain_context.chain_id,
        )

        if hasattr(txn, 'gas_price'):
            self.g.add_node(
                'GASPRICE',
                type=GASPRICE,
                value=txn.gas_price,
            )
        else:
            gas_price = vm.state.get_gas_price(txn)
            self.g.add_node(
                'GASPRICE',
                type=GASPRICE,
                value=gas_price
            )

        if hasattr(vm.get_header(), 'base_fee_per_gas'):
            self.g.add_node(
                'BASEFEE',
                type=BASEFEE,
                value=vm.get_header().base_fee_per_gas,
            )

        # first-call context
        self.g.add_node(
            'CALLER-1',
            type=CALLER,
            value=txn.sender,
        )
        self.g.add_node(
            'ADDRESS-1',
            type=ADDRESS,
            value=txn.to,
        )
        self.g.add_node(
            'SELFBALANCE-1',
            type=SELFBALANCE,
            value=vm.state.get_balance(txn.to) + txn.value if txn.to else txn.value,
        )
        self.g.add_node(
            'CALLVALUE-1',
            type=CALLVALUE,
            value=txn.value,
        )
        self.g.add_node(
            'CALLDATASIZE-1',
            type=CALLDATASIZE,
            value=len(txn.data),
        )
        self.g.add_node(
            'CALLDATA-1',
            type=CALLDATA,
            value=txn.data,
        )
        self.g.add_node(
            'CODESIZE-1',
            type=CODESIZE,
            value=len(vm.state.get_code(txn.to)) if txn.to else 0,
        )

    def pre_opcode_hook(self, opcode: Opcode, computation: ComputationAPI):
        if self.call_tracer.current_call_id not in self._shadow_stacks:
            # assume new call -- let's create all that we need
            self._shadow_stacks[self.call_tracer.current_call_id] = []
            self._shadow_memory[self.call_tracer.current_call_id] = []

        shadow_stack = self._shadow_stacks[self.call_tracer.current_call_id]
        assert len(shadow_stack) == len(computation._stack.values), f'expect shadow stack size {len(shadow_stack)} == stack size {len(computation._stack.values)}'

        if False:
            pass

        elif opcode.mnemonic == 'INVALID':
            pass # well...

        elif opcode.mnemonic in ['NUMBER', 'ORIGIN', 'TIMESTAMP', 'COINBASE', 'DIFFICULTY', 'GASLIMIT',
                                         'CHAINID', 'BASEFEE', 'GASPRICE', 'PREVRANDAO']:
            # transaction-level context, no args
            # special-case ID, since it's a constant
            id_ = opcode.mnemonic.lower()
            if not self.g.has_node(id_):
                self.g.add_node(id_, type=opcode.mnemonic.lower(), pc=computation.code.program_counter)
            shadow_stack.append(id_)

        elif opcode.mnemonic in ['CALLER', 'ADDRESS', 'CALLVALUE', 'CODESIZE', 'SELFBALANCE']:
            # call-level context, no args
            id_ = f'{opcode.mnemonic}-{self.call_tracer.current_call_id}'
            assert self.g.has_node(id_), f'node {id_} does not exist'
            shadow_stack.append(id_)

        elif opcode.mnemonic in ['PC']:
            id_ = f'{opcode.mnemonic}-{self.call_tracer.current_call_id}-{computation.code.program_counter}'
            if not self.g.has_node(id_):
                self.g.add_node(id_, type=opcode.mnemonic.lower(), pc=computation.code.program_counter)
            shadow_stack.append(id_)

        elif opcode.mnemonic in ['AND', 'OR', 'EQ', 'SHR', 'LT', 'GT', 'SLT', 'SGT', 'ADD', 'SUB',
                                        'SHL', 'SHR', 'MUL', 'DIV', 'EXP', 'XOR', 'SIGNEXTEND', 'MOD',
                                            'SDIV', 'SMOD', 'SAR']:
            # binary logic
            arg1 = read_stack_int(computation, 1)
            arg2 = read_stack_int(computation, 2)
            arg1_id = shadow_stack[-1]
            arg2_id = shadow_stack[-2]
            new_id = self.get_next_id()
            type_ = {
                'AND': AND, 'OR': OR, 'EQ': EQ, 'SHR': SHR, 'LT': LT, 'GT': GT,
                'SLT': SLT, 'SGT': SGT, 'ADD': ADD, 'SUB': SUB,
                'SHL': SHL, 'SHR': SHR, 'MUL': MUL, 'DIV': DIV, 'EXP': EXP,
                'XOR': XOR, 'SIGNEXTEND': SIGNEXTEND, 'MOD': MOD, 'SDIV': SDIV, 'SMOD': SMOD,
                'SAR': SAR}[opcode.mnemonic]
            self.g.add_node(new_id, type=type_, arg1=arg1, arg2=arg2, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            self.g.add_edge(arg1_id, new_id, argname='arg1')
            self.g.add_edge(arg2_id, new_id, argname='arg2')
            shadow_stack.pop()
            shadow_stack.pop()
            shadow_stack.append(new_id)

        elif opcode.mnemonic in ['MULMOD', 'ADDMOD']:
            arg1 = read_stack_int(computation, 1)
            arg2 = read_stack_int(computation, 2)
            arg3 = read_stack_int(computation, 3)
            arg1_id = shadow_stack[-1]
            arg2_id = shadow_stack[-2]
            arg3_id = shadow_stack[-3]
            new_id = self.get_next_id()
            type_ = {'MULMOD': MULMOD, 'ADDMOD': ADDMOD}[opcode.mnemonic]
            self.g.add_node(new_id, type=type_, arg1=arg1, arg2=arg2, arg3=arg3, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            self.g.add_edge(arg1_id, new_id, argname='arg1')
            self.g.add_edge(arg2_id, new_id, argname='arg2')
            self.g.add_edge(arg3_id, new_id, argname='arg3')
            shadow_stack.pop()
            shadow_stack.pop()
            shadow_stack.pop()
            shadow_stack.append(new_id)

        elif opcode.mnemonic in ['EXTCODESIZE']:
            # unary system queries
            arg1 = read_stack_int(computation, 1)
            arg1_id = shadow_stack[-1]
            new_id = self.get_next_id()
            type_ = {'EXTCODESIZE': EXTCODESIZE}[opcode.mnemonic]
            self.g.add_node(new_id, type=type_, arg1=arg1, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            self.g.add_edge(arg1_id, new_id, argname='arg1')
            shadow_stack.pop()
            shadow_stack.append(new_id)

        elif opcode.mnemonic in ['EXTCODECOPY']:
            address = read_stack_int(computation, 1)
            memOffset = read_stack_int(computation, 2)
            codeOffset = read_stack_int(computation, 3)
            size = read_stack_int(computation, 4)

            address_id = shadow_stack[-1]
            memOffset_id = shadow_stack[-2]
            codeOffset_id = shadow_stack[-3]
            size_id = shadow_stack[-4]

            new_id = self.get_next_id()

            type_ = {'EXTCODECOPY': EXTCODECOPY}[opcode.mnemonic]


            # TODO, get the code of the contract and set it as a value in the node
            #value = bytes(computation.code._raw_code_bytes[code_start_position:code_start_position+size].ljust(size, b'\x00'))

            self.g.add_node(new_id, type=type_, arg1=address, arg2=memOffset, arg3=codeOffset, arg4=size,
                                    call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)

            self.g.add_edge(address_id, new_id, argname='address')
            self.g.add_edge(memOffset_id, new_id, argname='memOffset')
            self.g.add_edge(codeOffset_id, new_id, argname='codeOffset')
            self.g.add_edge(size_id, new_id, argname='size')


            self._write_to_mem(self.call_tracer.current_call_id, memOffset, size, new_id)

            shadow_stack.pop()
            shadow_stack.pop()
            shadow_stack.pop()
            shadow_stack.pop()

        elif opcode.mnemonic in ['EXTCODEHASH']:
            target_address = read_stack_int(computation, 1)
            target_address_id = shadow_stack[-1]
            new_id = self.get_next_id()
            self.g.add_node(new_id, type=EXTCODEHASH, arg1=target_address, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            self.g.add_edge(target_address_id, new_id, argname='address')
            shadow_stack.pop()
            shadow_stack.append(new_id)

        elif opcode.mnemonic in ['BALANCE']:
            target_address = read_stack_int(computation, 1)
            target_address_id = shadow_stack[-1]
            new_id = self.get_next_id()
            self.g.add_node(new_id, type=BALANCE, arg1=target_address, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            self.g.add_edge(target_address_id, new_id, argname='address')
            shadow_stack.pop()
            shadow_stack.append(new_id)

        elif opcode.mnemonic in ['ISZERO', 'NOT']:
            # unary logic
            arg1 = read_stack_int(computation, 1)
            arg1_id = shadow_stack[-1]
            new_id = self.get_next_id()
            type_ = {'ISZERO': ISZERO, 'NOT': NOT}[opcode.mnemonic]
            self.g.add_node(new_id, type=type_, arg1=arg1, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            self.g.add_edge(arg1_id, new_id, argname='arg1')
            shadow_stack.pop()
            shadow_stack.append(new_id)

        elif opcode.mnemonic == 'BYTE':
            position = read_stack_int(computation, 1)
            value = read_stack_int(computation, 2)
            position_id = shadow_stack[-1]
            value_id = shadow_stack[-2]
            new_id = self.get_next_id()
            self.g.add_node(new_id, type=BYTE, position=position, value=value, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            self.g.add_edge(position_id, new_id, argname='position')
            self.g.add_edge(value_id, new_id, argname='value')
            shadow_stack.pop()
            shadow_stack.pop()
            shadow_stack.append(new_id)

        elif opcode.mnemonic == 'CREATE':
            value = read_stack_int(computation, 1)
            memOffset = read_stack_int(computation, 2)
            size = read_stack_int(computation, 3)

            value_id = shadow_stack[-1]
            memOffset_id = shadow_stack[-2]
            size_id = shadow_stack[-3]

            new_id = self.get_next_id()

            type_ = {'CREATE': CREATE}[opcode.mnemonic]

            to = calculate_create_contract_address(computation.msg.storage_address, computation.state.get_nonce(computation.msg.storage_address))

            # Let's see about this...
            to_id = self.get_next_id()
            self.g.add_node(to_id, type=ADDRESS, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)

            #TODO add the edges for the input that define the address if needed

            self.g.add_node(
                new_id,
                type=type_,
                to=to,
                value=value,
                memOffset=memOffset,
                size=size,
                call_id=self.call_tracer.current_call_id,
                pc=computation.code.program_counter,
            )

            self.g.add_edge(value_id, new_id, argname='value')
            self.g.add_edge(memOffset_id, new_id, argname='memOffset')
            self.g.add_edge(size_id, new_id, argname='size')

            self._setup_new_call(
                computation,
                self.call_tracer.next_call_id,
                new_id,
                value,
                to,
                memOffset,
                size,
                0,
                0,
                value_id,
                to_id,
                memOffset_id,
                size_id,
                -1,
                -1, # CHECK IF THIS IS OK
            )

            # Consume the four arguments
            shadow_stack.pop()
            shadow_stack.pop()
            shadow_stack.pop()

            # CREATE pushes 0x0 or the address of the deployed contract on the stack
            shadow_stack.append(new_id)

        elif opcode.mnemonic in ['CREATE2']:
            value = read_stack_int(computation, 1)
            memOffset = read_stack_int(computation, 2)
            size = read_stack_int(computation, 3)
            salt = read_stack_bytes(computation, 4)

            value_id = shadow_stack[-1]
            memOffset_id = shadow_stack[-2]
            size_id = shadow_stack[-3]
            salt_id = shadow_stack[-4]

            new_id = self.get_next_id()

            type_ = {'CREATE2': CREATE2}[opcode.mnemonic]

            to = calculate_create2_contract_address(computation.msg.storage_address, salt, computation._memory.read(memOffset, size).tobytes())

            # Let's see about this...
            to_id = self.get_next_id()
            self.g.add_node(to_id, type=ADDRESS, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)

            self.g.add_edge(salt_id, to_id, argname='salt')
            # TODO, add the other inputs

            self.g.add_node(
                new_id,
                type=type_,
                to=to,
                value=value,
                memOffset=memOffset,
                size=size,
                salt= int.from_bytes(salt, byteorder='big', signed=False) if isinstance(salt, bytes) else salt,
                call_id=self.call_tracer.current_call_id,
                pc=computation.code.program_counter,
            )

            self.g.add_edge(value_id, new_id, argname='value')
            self.g.add_edge(memOffset_id, new_id, argname='memOffset')
            self.g.add_edge(size_id, new_id, argname='size')
            self.g.add_edge(salt_id, new_id, argname='salt')

            self._setup_new_call(
                computation,
                self.call_tracer.next_call_id,
                new_id,
                value,
                to,
                memOffset,
                size,
                0,
                0,
                value_id,
                to_id,
                memOffset_id,
                size_id,
                -1,
                -1, # CHECK IF THIS IS OK
            )

            # Consume the four arguments
            shadow_stack.pop()
            shadow_stack.pop()
            shadow_stack.pop()
            shadow_stack.pop()

            # CREATE2 pushes 0x0 or the address of the deployed contract on the stack
            shadow_stack.append(new_id)

        elif opcode.mnemonic in ['STATICCALL', 'CALL', 'DELEGATECALL']:
            gas = read_stack_int(computation, 1)
            to = read_stack_int(computation, 2)
            i = 3
            if opcode.mnemonic == 'CALL':
                value = read_stack_int(computation, i)
                i += 1
            else:
                value = 0
            memory_input_start_position = read_stack_int(computation, i)
            memory_input_size = read_stack_int(computation, i+1)
            memory_output_start_position = read_stack_int(computation, i+2)
            memory_output_size = read_stack_int(computation, i+3)
            gas_id = shadow_stack.pop()
            to_id = shadow_stack.pop()
            if opcode.mnemonic == 'CALL':
                value_id = shadow_stack.pop()
            else:
                value_id = None
            memory_input_start_position_id = shadow_stack.pop()
            memory_input_size_id = shadow_stack.pop()
            memory_output_start_position_id = shadow_stack.pop()
            memory_output_size_id = shadow_stack.pop()

            type_ = {'STATICCALL': STATICCALL, 'CALL': CALL, 'DELEGATECALL': DELEGATECALL}[opcode.mnemonic]

            new_id = self.get_next_id()
            self.g.add_node(
                new_id,
                type=type_,
                gas=gas,
                to=to,
                value=value,
                memory_input_start_position=memory_input_start_position,
                memory_input_size=memory_input_size,
                memory_output_start_position=memory_output_start_position,
                memory_output_size=memory_output_size,
                call_id=self.call_tracer.current_call_id,
                pc=computation.code.program_counter,
            )
            self.g.add_edge(gas_id, new_id, argname='gas')
            self.g.add_edge(to_id, new_id, argname='to')
            self.g.add_edge(memory_input_start_position_id, new_id, argname='memory_input_start_position')
            self.g.add_edge(memory_input_size_id, new_id, argname='memory_input_size')
            self.g.add_edge(memory_output_start_position_id, new_id, argname='memory_output_start_position')
            self.g.add_edge(memory_output_size_id, new_id, argname='memory_output_size')
            if opcode.mnemonic == 'CALL':
                self.g.add_edge(value_id, new_id, argname='value')

            self._setup_new_call(
                computation,
                self.call_tracer.next_call_id,
                new_id,
                value,
                to,
                memory_input_start_position,
                memory_input_size,
                memory_output_start_position,
                memory_output_size,
                value_id,
                to_id,
                memory_input_start_position_id,
                memory_input_size_id,
                memory_output_start_position_id,
                memory_output_size_id,
            )

            # place the status on the stack
            shadow_stack.append(new_id)

        elif opcode.mnemonic == 'CALLDATACOPY':
            mem_start_position = read_stack_int(computation, 1)
            cd_start_position = read_stack_int(computation, 2)
            size = read_stack_int(computation, 3)
            mem_start_position_id = shadow_stack[-1]
            cd_start_position_id = shadow_stack[-2]
            cd_size_id = shadow_stack[-3]
            calldata_id = f'CALLDATA-{self.call_tracer.current_call_id}'

            value = computation.msg.data_as_bytes[
                cd_start_position : cd_start_position + size
            ].ljust(size, b'\x00')

            new_id = self.get_next_id()
            self.g.add_node(
                new_id,
                type=CALLDATACOPY,
                mem_start_position=mem_start_position,
                cd_start_position=cd_start_position,
                size=size,
                value=value,
                call_id=self.call_tracer.current_call_id,
                pc=computation.code.program_counter
            )

            self.g.add_edge(mem_start_position_id, new_id, argname='mem_start_position')
            self.g.add_edge(cd_start_position_id, new_id, argname='cd_start_position')
            self.g.add_edge(cd_size_id, new_id, argname='cd_size')
            self.g.add_edge(calldata_id, new_id, argname='calldata')

            # store the memory item
            self._write_to_mem(
                self.call_tracer.current_call_id,
                mem_start_position,
                size,
                new_id,
            )

            shadow_stack.pop()
            shadow_stack.pop()
            shadow_stack.pop()

        elif opcode.mnemonic == 'CALLDATALOAD':
            position_id = shadow_stack[-1]
            calldata_id = f'CALLDATA-{self.call_tracer.current_call_id}'
            new_id = self.get_next_id()
            # what are we loading?
            v = read_stack_int(computation, 1)
            self.g.add_node(new_id, type=CALLDATALOAD, position=v, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            self.g.add_edge(shadow_stack[-1], new_id, argname='position')
            self.g.add_edge(calldata_id, new_id, argname='calldata')
            shadow_stack[-1] = new_id

        elif opcode.mnemonic == 'CALLDATASIZE':
            id_ = f'CALLDATASIZE-{self.call_tracer.current_call_id}'
            assert self.g.has_node(id_)
            shadow_stack.append(id_)

        elif opcode.mnemonic.startswith('DUP'):
            ndup = int(opcode.mnemonic[3:])
            assert 0 < ndup <= len(shadow_stack)
            shadow_stack.append(shadow_stack[-ndup])
            '''
            new_id = self.get_next_id()
            self.g.add_node(new_id, type=DUP, ndup=ndup, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            self.g.add_edge(shadow_stack[-ndup], new_id, argname='dup')
            shadow_stack.append(new_id)
            '''

            '''
            #import ipdb; ipdb.set_trace()
            new_id = self.get_next_id()
            to_duplicate = self.g.nodes[shadow_stack[-ndup]]
            # add the exact same node but with different new_id, pass all the attributes
            self.g.add_node(new_id, **to_duplicate)
            import ipdb; ipdb.set_trace()
            shadow_stack.append(new_id)
            '''

        elif opcode.mnemonic == "MSIZE":
            new_id = self.get_next_id()
            self.g.add_node(new_id, type=opcode.mnemonic.lower(), pc=computation.code.program_counter)
            shadow_stack.append(new_id)

        elif opcode.mnemonic == 'GAS':
            # GAS changes a lot and we don't really care to track it
            new_id = self.get_next_id()
            self.g.add_node(new_id, type=GAS, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            shadow_stack.append(new_id)

        elif opcode.mnemonic in ['JUMPDEST']:
            # nop (for us)
            pass

        elif opcode.mnemonic == 'STOP':
            if self.call_tracer.current_call_id != 1:
                new_id = self.get_next_id()
                call_details = self._shadow_call_details[self.call_tracer.current_call_id]
                self._shadow_returndata[call_details.parent_call_id] = None

        elif opcode.mnemonic == 'JUMP':
            jump_dest = read_stack_int(computation, 1)
            jump_dest_id = shadow_stack[-1]
            new_id = self.get_next_id()
            self.g.add_node(new_id, type=JUMP, jump_dest=jump_dest, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            self.g.add_edge(jump_dest_id, new_id, argname='jump_dest')
            shadow_stack.pop()

        elif opcode.mnemonic == 'JUMPI':
            jump_dest = read_stack_int(computation, 1)
            check_value = read_stack_int(computation, 2)
            jump_dest_id = shadow_stack[-1]
            check_value_id = shadow_stack[-2]
            new_id = self.get_next_id()
            self.g.add_node(new_id, type=JUMPI, jump_dest=jump_dest, check_value=check_value, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            self.g.add_edge(jump_dest_id, new_id, argname='jump_dest')
            self.g.add_edge(check_value_id, new_id, argname='check_value')
            shadow_stack.pop()
            shadow_stack.pop()

        elif opcode.mnemonic.startswith('LOG'):
            nlog = int(opcode.mnemonic[3:])
            assert 0 < nlog <= len(shadow_stack)

            mem_start = read_stack_int(computation, 1)
            mem_size = read_stack_int(computation, 2)
            mem_start_id = shadow_stack.pop()
            mem_size_id = shadow_stack.pop()

            new_id = self.get_next_id()

            topic_ids = []
            topic_vals = []
            for i in range(nlog):
                ref_id = shadow_stack.pop()
                val = read_stack_int(computation, i+3)
                topic_ids.append(ref_id)
                topic_vals.append(val)

            self.g.add_node(
                new_id,
                type=LOG,
                start_position=mem_start,
                size=mem_size,
                call_id=self.call_tracer.current_call_id,
                pc=computation.code.program_counter,
                **{f'topic-{i}': val for i, val in enumerate(topic_vals)},
            )

            self.g.add_edge(mem_start_id, new_id, argname='start_position')
            self.g.add_edge(mem_size_id, new_id, argname='size')

            for i, ref_id in enumerate(topic_ids):
                assert self.g.has_node(ref_id)
                self.g.add_edge(ref_id, new_id, argname=f'log-topic-{i}')

            # add in edges from memory items that overlap with the start_position and size
            for i, mem_item in enumerate(self._get_referenced_mem_items(self.call_tracer.current_call_id, mem_start, mem_size)):
                self.g.add_edge(mem_item.id_, new_id, argname=f'memory-{i}')

        elif opcode.mnemonic == 'RETURN':
            start_position = read_stack_int(computation, 1)
            size = read_stack_int(computation, 2)
            start_position_id = shadow_stack[-1]
            size_id = shadow_stack[-2]
            new_id = self.get_next_id()
            retval = computation._memory.read_bytes(start_position, size).ljust(size, b'\x00')

            self.g.add_node(new_id, type=RETURN, start_position=start_position, value=retval, size=size, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            self.g.add_edge(start_position_id, new_id, argname='start_position')
            self.g.add_edge(size_id, new_id, argname='size')
            # add in edges from memory items that overlap with the start_position and size
            for i, mem_item in enumerate(self._get_referenced_mem_items(self.call_tracer.current_call_id, start_position, size)):
                self.g.add_edge(mem_item.id_, new_id, argname=f'memory-{i}')

            shadow_stack.pop()
            shadow_stack.pop()

            # if this is not the root call, we need to set the return data and modify the parent call's memory
            if self.call_tracer.current_call_id != 1:
                call_details = self._shadow_call_details[self.call_tracer.current_call_id]
                self._shadow_returndata[call_details.parent_call_id] = _ReturndataItem(
                    value_id=new_id,
                    size_id=size_id,
                    size=size,
                    value=retval,
                )
                self._write_to_mem(
                    call_details.parent_call_id,
                    call_details.returndata_position,
                    call_details.returndata_size,
                    new_id,
                )

        elif opcode.mnemonic == 'SHA3':
            start_position = read_stack_int(computation, 1)
            size = read_stack_int(computation, 2)
            start_position_id = shadow_stack[-1]
            size_id = shadow_stack[-2]
            if size_id == 99:
                l.warning('SHA3 size_id is 99... problem')
            new_id = self.get_next_id()
            self.g.add_node(new_id, type=SHA3, start_position=start_position, size=size, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            self.g.add_edge(start_position_id, new_id, argname='start_position')
            self.g.add_edge(size_id, new_id, argname='size')
            # add in edges from memory items that overlap with the start_position and size
            for i, mem_item in enumerate(self._get_referenced_mem_items(self.call_tracer.current_call_id, start_position, size)):
                self.g.add_edge(mem_item.id_, new_id, argname=f'memory-{i}')
            shadow_stack.pop()
            shadow_stack.pop()
            shadow_stack.append(new_id)

        elif opcode.mnemonic == 'SSTORE':
            slot = read_stack_int(computation, 1)
            value = read_stack_int(computation, 2)
            slot_id = shadow_stack[-1]
            value_id = shadow_stack[-2]
            new_id = self.get_next_id()
            self.g.add_node(new_id, type=SSTORE, slot=slot, value=value, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            self.g.add_edge(slot_id, new_id, argname='slot')
            self.g.add_edge(value_id, new_id, argname='value')
            shadow_stack.pop()
            shadow_stack.pop()
            storage_address = web3.Web3.to_checksum_address(computation.msg.storage_address)
            self._shadow_storage[storage_address][slot] = _StorageItem(
                id_=new_id,
                slot=slot,
                value=value,
            )

        elif opcode.mnemonic == 'SLOAD':
            slot = read_stack_int(computation, 1)
            slot_id = shadow_stack[-1]
            storage_address = web3.Web3.to_checksum_address(computation.msg.storage_address)
            if slot in self._shadow_storage[storage_address]:
                value_id = self._shadow_storage[storage_address][slot].id_
            else:
                node_id = f'STORAGE-{storage_address}-{hex(slot)}'
                if not self.g.has_node(node_id):
                    self.g.add_node(node_id, type=EXISTING_STORAGE, slot=slot, call_id=self.call_tracer.current_call_id)
                value_id = node_id

            new_id = self.get_next_id()
            self.g.add_node(new_id, type=SLOAD, slot=slot, storage_address=storage_address, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            self.g.add_edge(slot_id, new_id, argname='slot')
            self.g.add_edge(value_id, new_id, argname='value')
            shadow_stack.pop()
            shadow_stack.append(new_id)

        elif opcode.mnemonic == 'MLOAD':
            position = read_stack_int(computation, 1)
            position_id = shadow_stack[-1]
            new_id = self.get_next_id()
            self.g.add_node(new_id, type=MLOAD, position=position, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            self.g.add_edge(position_id, new_id, argname='position')
            # add in edges from memory items that overlap with the start_position and size
            for i, mem_item in enumerate(self._get_referenced_mem_items(self.call_tracer.current_call_id, position, 32)):
                self.g.add_edge(mem_item.id_, new_id, argname=f'memory-{i}')
            shadow_stack.pop()
            shadow_stack.append(new_id)

        elif opcode.mnemonic == 'MSTORE':
            start_position = read_stack_int(computation, 1)
            value = read_stack_int(computation, 2)
            start_position_id = shadow_stack[-1]
            value_id = shadow_stack[-2]
            new_id = self.get_next_id()
            self.g.add_node(new_id, type=MSTORE, start_position=start_position, value=value, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            self.g.add_edge(start_position_id, new_id, argname='start_position')
            self.g.add_edge(value_id, new_id, argname='value')
            shadow_stack.pop()
            shadow_stack.pop()
            self._write_to_mem(self.call_tracer.current_call_id, start_position, 32, new_id)

        elif opcode.mnemonic == 'MSTORE8':
            start_position = read_stack_int(computation, 1)
            value = read_stack_int(computation, 2)
            start_position_id = shadow_stack[-1]
            value_id = shadow_stack[-2]
            new_id = self.get_next_id()
            self.g.add_node(new_id, type=MSTORE8, start_position=start_position, value=value, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            self.g.add_edge(start_position_id, new_id, argname='start_position')
            self.g.add_edge(value_id, new_id, argname='value')
            shadow_stack.pop()
            shadow_stack.pop()
            self._write_to_mem(self.call_tracer.current_call_id, start_position, 1, new_id)

        elif opcode.mnemonic == 'POP':
            shadow_stack.pop()

        elif opcode.mnemonic.startswith('PUSH'):
            size = int(opcode.mnemonic[4:])
            raw_value = computation.code._raw_code_bytes[computation.code.program_counter:computation.code.program_counter+size]
            value = int.from_bytes(raw_value, byteorder='big', signed=False)
            new_id = self.get_next_id()
            self.g.add_node(new_id, type=PUSH, value=value, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            shadow_stack.append(new_id)
            assert shadow_stack[-1] == new_id

        elif opcode.mnemonic == 'RETURNDATASIZE':
            my_shadow_returndata = self._shadow_returndata.get(self.call_tracer.current_call_id, None)
            if my_shadow_returndata is None:
                # no returndata record -- it will return the value 0 and is disconnected
                empty_returndata_id = f'RETURNDATASIZE-empty-{self.call_tracer.current_call_id}'
                if not self.g.has_node(empty_returndata_id):
                    self.g.add_node(empty_returndata_id, type=RETURNDATASIZE, call_id=self.call_tracer.current_call_id)
                shadow_stack.append(empty_returndata_id)
            else:
                new_id = self.get_next_id()
                self.g.add_node(new_id, type=RETURNDATASIZE, value=my_shadow_returndata.size, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
                self.g.add_edge(my_shadow_returndata.size_id, new_id, argname='size')
                shadow_stack.append(new_id)

        elif opcode.mnemonic == 'RETURNDATACOPY':
            mem_start_position = read_stack_int(computation, 1)
            returndata_start_position = read_stack_int(computation, 2)
            size = read_stack_int(computation, 3)
            mem_start_position_id = shadow_stack[-1]
            returndata_start_position_id = shadow_stack[-2]
            size_id = shadow_stack[-3]

            my_shadow_returndata = self._shadow_returndata.get(self.call_tracer.current_call_id, None)
            if my_shadow_returndata is None:
                # this means there was probably a STOP (so nothing was effectively returned).
                pass
            else:
                new_id = self.get_next_id()
                self.g.add_node(
                    new_id,
                    type=RETURNDATACOPY,
                    mem_start_position=mem_start_position,
                    returndata_start_position=returndata_start_position,
                    size=size,
                    call_id=self.call_tracer.current_call_id,
                    pc=computation.code.program_counter,
                )
                self.g.add_edge(mem_start_position_id, new_id, argname='mem_start_position')
                self.g.add_edge(returndata_start_position_id, new_id, argname='returndata_start_position')
                self.g.add_edge(size_id, new_id, argname='size')
                self.g.add_edge(my_shadow_returndata.value_id, new_id, argname='returndata')
                self._write_to_mem(self.call_tracer.current_call_id, mem_start_position, size, new_id)
            shadow_stack.pop()
            shadow_stack.pop()
            shadow_stack.pop()

        elif opcode.mnemonic.startswith('SWAP'):
            nswap = int(opcode.mnemonic[4:])
            assert 0 < nswap <= len(shadow_stack)
            shadow_stack[-1], shadow_stack[-(nswap+1)] = shadow_stack[-(nswap+1)], shadow_stack[-1]

        elif opcode.mnemonic.startswith('CODECOPY'):
            mem_start_position = read_stack_int(computation, 1)
            code_start_position = read_stack_int(computation, 2)
            size = read_stack_int(computation, 3)

            dest_offset_id = shadow_stack[-1]
            code_offset_id = shadow_stack[-2]
            size_id = shadow_stack[-3]
            new_id = self.get_next_id()

            value = bytes(computation.code._raw_code_bytes[code_start_position:code_start_position+size].ljust(size, b'\x00'))

            self.g.add_node(
                new_id,
                type=CODECOPY,
                mem_start_position=mem_start_position,
                code_start_position=code_start_position,
                size=size,
                value=value,
                call_id=self.call_tracer.current_call_id,
                pc=computation.code.program_counter,
            )

            self.g.add_edge(dest_offset_id, new_id, argname='mem_start_position')
            self.g.add_edge(code_offset_id, new_id, argname='code_start_position')
            self.g.add_edge(size_id, new_id, argname='size')

            self._write_to_mem(self.call_tracer.current_call_id, mem_start_position, size, new_id)

            shadow_stack.pop()
            shadow_stack.pop()
            shadow_stack.pop()

        elif opcode.mnemonic == 'REVERT':
            mem_start_position = read_stack_int(computation, 1)
            size = read_stack_int(computation, 2)
            # reverts takes the memory at memOffset and copies 'size' bytes
            # in the returndata buffer of the EVM.
            memOffset_id = shadow_stack[-1]
            size_id = shadow_stack[-2]
            new_id = self.get_next_id()

            self.g.add_node(new_id, type=REVERT, memOffset=mem_start_position, size=size,
                            call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)

            self.g.add_edge(memOffset_id, new_id, argname='mem_start_position')
            self.g.add_edge(size_id, new_id, argname='size')

            # add in edges from memory items that overlap with the start_position and size
            for i, mem_item in enumerate(self._get_referenced_mem_items(self.call_tracer.current_call_id, mem_start_position, size)):
                self.g.add_edge(mem_item.id_, new_id, argname=f'memory-{i}')

            retval = computation._memory.read_bytes(mem_start_position, size).ljust(size, b'\x00')

            shadow_stack.pop()
            shadow_stack.pop()

            # if this is not the root call, we need to set the return data and modify the parent call's memory
            if self.call_tracer.current_call_id != 1:
                call_details = self._shadow_call_details[self.call_tracer.current_call_id]
                self._shadow_returndata[call_details.parent_call_id] = _ReturndataItem(
                    value_id=new_id,
                    size_id=size_id,
                    size=size,
                    value=retval,
                )
                self._write_to_mem(
                    call_details.parent_call_id,
                    call_details.returndata_position,
                    call_details.returndata_size,
                    new_id,
                )

            # The value 0 is pushed on the stack as per doc.
            shadow_stack.append(new_id)

        elif opcode.mnemonic == 'SELFDESTRUCT':
            beneficiary = read_stack_int(computation, 1)
            beneficiary_id = shadow_stack[-1]

            new_id = self.get_next_id()
            self.g.add_node(new_id, type=SELFDESTRUCT, beneficiary=beneficiary, call_id=self.call_tracer.current_call_id, pc=computation.code.program_counter)
            self.g.add_edge(beneficiary_id, new_id, argname='beneficiary')

            shadow_stack.pop()

        elif opcode.mnemonic == 'BLOCKHASH':
            block_number = read_stack_int(computation, 1)
            block_number_id = shadow_stack[-1]

            node_id = f'BLOCKHASH-{block_number}'
            if not self.g.has_node(node_id):
                self.g.add_node(node_id, type=BLOCKHASH, block_number=block_number)
            self.g.add_edge(block_number_id, node_id, argname='block_number')

            shadow_stack.pop()
            shadow_stack.append(node_id)

        else:
            # need to handle each and every opcode!
            raise NotImplementedError(f'Have not implemented opcode {opcode.mnemonic} yet')

    def get_next_id(self):
        id_ = self.next_id
        self.next_id = id_ + 1
        return id_

    def _setup_new_call(
            self,
            computation: ComputationAPI,
            new_call_id: int,
            new_call_graph_id: int,
            value: int,
            to: int,
            input_start_position: int,
            input_size: int,
            output_start_position: int,
            output_size: int,
            value_id: int,
            to_id: int,
            input_start_position_id: int,
            input_size_id: int,
            output_start_position_id: int,
            output_size_id: int,
        ):
        """
        Setup a new call (assumed we are not yet in it)
        """
        assert self.call_tracer.current_call_id != new_call_id, f'new call id {new_call_id} must be different from current call id {self.call_tracer.current_call_id}'

        # create the new call context
        self.g.add_node(
            f'CALLER-{new_call_id}',
            type=CALLER,
            value=self.call_tracer.call_stack[-1].callee,
        )
        self.g.add_node(
            f'ADDRESS-{new_call_id}',
            type=ADDRESS,
            value=to,
        )
        self.g.add_node(
            f'CALLVALUE-{new_call_id}',
            type=CALLVALUE,
            value=value,
        )
        self.g.add_node(
            f'CALLDATASIZE-{new_call_id}',
            type=CALLDATASIZE,
            value=input_size,
        )
        self.g.add_node(
            f'CALLDATA-{new_call_id}',
            type=CALLDATA,
            value=computation._memory.read_bytes(input_start_position, input_size),
        )

        self.g.add_node(
            f'SELFBALANCE-{new_call_id}',
            type=CALLDATA,
            value=computation._memory.read_bytes(input_start_position, input_size),
        )

        self.g.add_node(
            f'CODESIZE-{new_call_id}',
            type=CODESIZE,
            value=len(computation.code),
        )

        # add edges to track source
        if value_id is not None:
            self.g.add_edge(value_id, f'CALLVALUE-{new_call_id}', argname='value')
            self.g.add_edge(new_call_graph_id, f'CALLVALUE-{new_call_id}', argname='src_call')
        self.g.add_edge(to_id, f'ADDRESS-{new_call_id}', argname='to')
        self.g.add_edge(new_call_graph_id, f'ADDRESS-{new_call_id}', argname='src_call')
        self.g.add_edge(input_start_position_id, f'CALLDATA-{new_call_id}', argname='input_start_position')
        self.g.add_edge(new_call_graph_id, f'CALLDATA-{new_call_id}', argname='src_call')
        self.g.add_edge(input_size_id, f'CALLDATA-{new_call_id}', argname='input_size')
        self.g.add_edge(new_call_graph_id, f'CALLDATA-{new_call_id}', argname='src_call')
        self.g.add_edge(input_size_id, f'CALLDATASIZE-{new_call_id}', argname='input_size')
        self.g.add_edge(new_call_graph_id, f'CALLDATASIZE-{new_call_id}', argname='src_call')
        self.g.add_edge(f'ADDRESS-{self.call_tracer.current_call_id}', f'CALLER-{new_call_id}', argname='caller')
        self.g.add_edge(new_call_graph_id, f'CALLER-{new_call_id}', argname='src_call')

        # add edge out of call node, just to track it

        # add edges for memory
        for i, mem_item in enumerate(self._get_referenced_mem_items(self.call_tracer.current_call_id, input_start_position, input_size)):
            self.g.add_edge(mem_item.id_, f'CALLDATA-{new_call_id}', argname=f'memory-{i}')

        self._shadow_call_details[new_call_id] = _CallContext(
            parent_call_id=self.call_tracer.current_call_id,
            returndata_position=output_start_position,
            returndata_size=output_size,
            returndata_position_id=output_start_position_id,
            returndata_size_id=output_size_id,
        )

    def _write_to_mem(self, call_id: int, start_position: int, size: int, id_: int):
        assert(type(start_position) == int)

        if call_id not in self._shadow_memory:
            self._shadow_memory[call_id] = []
        shadow_memory = self._shadow_memory[call_id]

        if len(shadow_memory) > 0:
            assert id_ > shadow_memory[-1].id_, f'new id {id_} must be greater than last id {shadow_memory[-1].id_}'
        shadow_memory.append(_MemoryItem(
            id_=id_,
            start_position=start_position,
            size=size,
        ))

    def _get_referenced_mem_items(self, call_id: int, start_position: int, size: int) -> typing.List['_MemoryItem']:
        """
        Returns a list of active memory items that overlap with the given start_position and size.

        NOTE the use of 'active' - this means that the memory item must be alive at the time of the call, some memory
        items may have been overwritten by later MSTOREs, and thus are not active and are not returned.
        """
        if call_id not in self._shadow_memory:
            return []

        ret = []
        # use a bit-mask to iterate until we have no more unreferenced bytes
        # each bit represents a byte in the memory
        # 0 = unreferenced, 1 = referenced
        mask = 0
        target_mask = (1 << size) - 1
        for mem_item in reversed(self._shadow_memory[call_id]):
            if mask == target_mask:
                # we have all the items we need
                break
            # check if this memory item overlaps with the target
            if mem_item.start_position + mem_item.size <= start_position:
                # this memory item is before the target
                continue
            if mem_item.start_position >= start_position + size:
                # this memory item is after the target
                continue

            # this memory item overlaps with the target

            # compute the mask for this memory item
            mem_mask = (1 << mem_item.size) - 1

            # shift the mask so that it shows overlap with the target
            if mem_item.start_position < start_position:
                # this memory item starts before the target
                # compute the mask for the bytes before the target
                # shift mask to the right by the number of bytes before the target
                mem_mask >>= (start_position - mem_item.start_position)
            else:
                # this memory item starts at or after the target
                # shift mask to the left by the number of bytes after the target
                mem_mask <<= (mem_item.start_position - start_position)

            # do we have any unset bits in the mask?
            if mem_mask & mask == mem_mask:
                # no, this value was entirely overwritten by a later MSTORE, skip it
                continue

            # we have some bits that are not set, so this memory item is active
            ret.append(mem_item)

            # update the mask
            mask |= mem_mask
        return ret

    def pretty_print_graph(self, output=None):
        """
        print the graph in graphviz format
        """
        pretty_print_graph(self.g, output=output)


def pretty_print_graph(g: nx.MultiDiGraph, output=None, highlight_nodes: typing.Iterable[typing.Union[str, int]]=None):
    """
    print the graph in graphviz format
    """
    if len(g.nodes) > 1_000 and output is None:
        print('    "Too many nodes to print";')
        return
    
    file = open(output, 'a')

    print('digraph {', file=file)
    # set background color to white
    print('    bgcolor="white";', file=file)
    # change node to rectangle
    print('    node [shape=record];', file=file)
    for id_, data in g.nodes(data=True):
        # special case for calldata - format in blocks of 32
        extra_props = ''
        if data['type'] == CALLDATA:
            sz_data_builder = []
            # print first four bytes
            sz_data_builder.append(f'calldata[000:004]={data["value"][0:4].hex()} .......................................................')
            # print the rest in blocks of 32
            for i in range(4, len(data['value']), 32):
                sz_data_builder.append(f'calldata[{i:03x}:{i+32:03x}]={data["value"][i:i+32].hex()}')
            sz_data = '\\n'.join(sz_data_builder)
            extra_props = 'fontname="Courier New"'
        else:
            sz_data_builder = []
            for k, v in data.items():
                if k == 'type':
                    continue
                if isinstance(v, int):
                    sz_val = hex(v)
                elif isinstance(v, bytes):
                    sz_val = bytes(v).hex()
                    if len(sz_val) > 32:
                        sz_val = sz_val[:32] + '...'
                elif isinstance(v, str):
                    sz_val = v
                sz_data_builder.append(f'{k}={sz_val}')
            sz_data = '\\n'.join(sz_data_builder)
        if highlight_nodes is not None and id_ in highlight_nodes:
            extra_props += ' color="red"'
        print(f'    "{id_}" [label="id={id_}\\n{data["type"]}\\n{sz_data}" {extra_props}];', file=file)

    for src, dst, data in g.edges(data=True):
        sz_data_builder = []
        for k, v in data.items():
            if k == 'argname':
                continue
            if isinstance(v, int):
                sz_val = hex(v)
            elif isinstance(v, bytes):
                sz_val = bytes(v).hex()
            sz_data_builder.append(f'{k}={sz_val}')
        sz_data = '\\n'.join(sz_data_builder)
        print(f'    "{src}" -> "{dst}" [label="{data["argname"]}\\n{sz_data}"];', file=file)

    print('}', file=file)

class _MemoryItem(typing.NamedTuple):
    id_: int
    start_position: int
    size: int

    @property
    def end_position(self):
        return self.start_position + self.size

class _StorageItem(typing.NamedTuple):
    id_: int
    slot: int
    value: int

class _ReturndataItem(typing.NamedTuple):
    value_id: int
    size_id: int
    size: int
    value: bytes

class _CallContext(typing.NamedTuple):
    parent_call_id: int
    returndata_position: int
    returndata_size: int
    returndata_position_id: int
    returndata_size_id: int