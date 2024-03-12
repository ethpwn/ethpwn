import enum
import typing

from eth._utils.address import (generate_contract_address,
                                generate_safe_contract_address)
from eth.abc import MessageAPI
from eth.exceptions import Halt, Revert
from eth.vm.logic.call import CallParams

from .base import *


class CallType(enum.Enum):
    CALL = 'CALL'
    CALLCODE = 'CALLCODE'
    CREATE = 'CREATE'
    CREATE2 = 'CREATE2'
    DELEGATECALL = 'DELEGATECALL'
    SELFDESTRUCT = 'SELFDESTRUCT'
    STATICCALL = 'STATICCALL'


class TracedCall(typing.NamedTuple):
    id: int
    actions: typing.List['TracedCall']
    call_type: 'CallType'
    calldata: typing.Optional[bytes]
    callee: str # the code address that was called
    caller: typing.Optional[str] # the code address that invoked the call
    error: typing.Optional[str]
    gas_limit: int
    gas_used: int
    is_error: bool
    pc: typing.Optional[int]
    returndata: typing.Optional[bytes]
    reverted: bool
    storage_address: str  # the address used for storage within the call (in the case of DELEGATECALL, this is different than callee)
    value: int

class CallTracer(BaseAnalysisPlugin):

    name = "call_tracer"

    next_op_id: int
    call_stack: typing.Deque[TracedCall]
    root_call: TracedCall
    last_op_threw: bool
    txn: SignedTransactionMethods

    @property
    def current_call_id(self) -> int:
        return self.call_stack[-1].id

    def pre_transaction_hook(self, vm: VM, txn: SignedTransactionMethods):
        self.txn = txn

        root_call = TracedCall(
            id=1,
            actions=[],
            call_type=CallType.CALL,
            calldata=txn.data,
            callee=txn.to,
            caller=txn.sender,
            error=None,
            gas_limit=None,
            gas_used=None,
            is_error=False,
            pc=0x0,
            returndata=None,
            reverted=False,
            storage_address=txn.to,
            value=txn.value,
        )

        if txn.to == b'':
            nonce_at_start = vm.state.get_nonce(txn.sender)
            address = generate_contract_address(
                txn.sender,
                nonce_at_start,
            )
            root_call = root_call._replace(
                callee = address,
                storage_address = address,
                call_type = CallType.CREATE,
            )

        self.call_stack = typing.Deque([root_call])
        self.next_call_id = 2

    def pre_opcode_hook(self, opcode: Opcode, computation: ComputationAPI):
        self.last_op_threw = False

        #
        # Safety asserts
        #
        if self.call_stack[-1].call_type in [CallType.CREATE, CallType.CREATE2]:
            assert computation.msg.storage_address == self.call_stack[-1].storage_address, \
                f'expect {computation.msg.storage_address.hex()} == {self.call_stack[-1].storage_address.hex()}'
        else:
            assert computation.msg.code_address == self.call_stack[-1].callee, \
                f'expect {computation.msg.code_address} == {self.call_stack[-1].callee}'

        if computation.msg.depth +1 != len(self.call_stack):
            # depth mismatch -- bug!!!!
            raise Exception('depth mismatch')

        #
        # Fill gas info if needed
        #
        if self.call_stack[-1].gas_limit is None:
            self.call_stack.append(self.call_stack.pop()._replace(
                gas_limit = computation.get_gas_remaining()
            ))

        #
        # Instruction handling
        #

        if opcode.mnemonic in ['CALL', 'STATICCALL', 'DELEGATECALL', 'CALLCODE', 'CREATE', 'CREATE2']:
            error: typing.Optional[str] = None

            if opcode.mnemonic in ['CALL', 'STATICCALL', 'CALLCODE', 'DELEGATECALL']:
                # reading params pops from the stack :( so we do a trick to restore old state
                old_stack = computation._stack.values.copy()
                params: CallParams = opcode.get_call_params(computation)
                computation._stack.values.clear()
                computation._stack.values.extend(old_stack)

                (
                    gas,
                    value,
                    to,
                    sender,
                    code_address,
                    memory_input_start_position,
                    memory_input_size,
                    memory_output_start_position,
                    memory_output_size,
                    should_transfer_value,
                    is_static,
                ) = params

                storage_address = to
                storage_address = storage_address.rjust(20, b'\x00')

                callee = code_address if code_address is not None else to
                callee = callee.rjust(20, b'\x00')
                if computation.state.get_code(callee) == b'':
                    error = 'NO CODE'
                calldata = None # filled later

            else:
                # this is a CREATE (or CREATE2)
                # reading params pops from the stack :( so we do a trick to restore old state
                old_stack = computation._stack.values.copy()
                params = opcode.get_stack_data(computation)
                computation._stack.values.clear()
                computation._stack.values.extend(old_stack)

                value = params.endowment
                calldata = computation.memory_read_bytes(params.memory_start, params.memory_length)
                calldata = bytes(calldata).ljust(params.memory_length, b'\x00')

                # compute the address
                if opcode.mnemonic == 'CREATE':
                    address = generate_contract_address(
                        computation.msg.storage_address,
                        computation.state.get_nonce(computation.msg.storage_address),
                    )
                else:
                    assert opcode.mnemonic == 'CREATE2'
                    address = generate_safe_contract_address(
                        computation.msg.storage_address,
                        params.salt,
                        calldata
                    )
                storage_address = address
                callee = address

            self.call_stack.append(TracedCall(
                actions=[],
                call_type={
                    'CALL': CallType.CALL,
                    'STATICCALL': CallType.STATICCALL,
                    'CALLCODE': CallType.CALLCODE,
                    'DELEGATECALL': CallType.DELEGATECALL,
                    'CREATE': CallType.CREATE,
                    'CREATE2': CallType.CREATE2
                }[opcode.mnemonic],
                id=self.next_call_id,
                calldata=calldata,
                callee=callee,
                caller=computation.msg.storage_address,
                error=error,
                gas_limit=None, # will be set later
                gas_used=None,
                is_error=False,
                pc=computation.code.program_counter,
                returndata=None,
                reverted=False,
                storage_address=storage_address,
                value=value,
            ))
            self.next_call_id += 1

            old_apply = computation.apply_child_computation
            def new_apply(child_msg: MessageAPI, old_apply=old_apply, old_computation=computation, tracer=self):
                # restore
                old_computation.apply_child_computation = old_apply
                to_update = {'gas_limit': child_msg.gas}
                if not child_msg.is_create:
                    to_update['calldata'] = child_msg.data_as_bytes
                tracer.call_stack.append(tracer.call_stack.pop()._replace(**to_update))

                ret = old_apply(child_msg)
                tracer.call_stack.append(tracer.call_stack.pop()._replace(
                    gas_used = ret.get_gas_used(),
                ))
                return ret
            computation.apply_child_computation = new_apply

        elif opcode.mnemonic == 'SELFDESTRUCT':
            beneficiary_type, beneficiary = (computation._stack.values or [(int, 0)])[-1]
            if beneficiary_type == int:
                beneficiary = int.to_bytes(beneficiary, length=20, signed=False, byteorder='big')
            else:
                beneficiary = bytes(beneficiary[-20:]).rjust(20, b'\x00')
            local_balance = computation.state.get_balance(computation.msg.storage_address)

            # the call ended in a selfdestruct, add that to the actions list
            self.call_stack[-1].actions.append(TracedCall(
                id=self.next_call_id,
                actions=[],
                call_type=CallType.SELFDESTRUCT,
                calldata=b'',
                callee=beneficiary,
                caller=computation.msg.storage_address,
                error=None,
                gas_limit=0,
                gas_used=0,
                is_error=False,
                pc=None,
                returndata=None,
                reverted=False,
                storage_address=None,
                value=local_balance,
            )),
            self.next_call_id += 1

    def post_opcode_hook(self, opcode: Opcode, computation: ComputationAPI):
        if self.last_op_threw:
            # wrapped up in exception handler
            return

        if opcode.mnemonic in ['CALL', 'STATICCALL', 'CALLCODE', 'DELEGATECALL', 'CREATE', 'CREATE2']:
            # call just finished, wrap up
            finished_call = self.call_stack.pop()
            is_error_type, error_flag = computation._stack.values[-1]
            if is_error_type == bytes:
                error_flag = int.from_bytes(error_flag, byteorder='big', signed=False)

            finished_call = finished_call._replace(
                # returndata=computation.return_data,
                is_error=error_flag == 0,
            )
            self.call_stack[-1].actions.append(finished_call)
            assert len(self.call_stack[-1].actions) > 0

    def opcode_exception_hook(self, opcode: Opcode, computation: ComputationAPI, e: Exception):
        self.last_call_threw = True

        if isinstance(e, Revert):
            self.call_stack.append(self.call_stack.pop()._replace(
                reverted=True,
            ))
        elif isinstance(e, Halt) and str(e) == 'RETURN':
            if self.call_stack[-1].call_type not in [CallType.CREATE, CallType.CREATE2]:
                self.call_stack.append(self.call_stack.pop()._replace(
                    returndata=computation.output,
                ))
        elif not isinstance(e, Halt):
            if opcode.mnemonic in ['CALL', 'STATICCALL', 'CALLCODE', 'DELEGATECALL', 'CREATE', 'CREATE2']:
                # call completed in error
                finished_call = self.call_stack.pop()
                finished_call = finished_call._replace(
                    is_error=True,
                    error=str(e),
                )
                self.call_stack[-1].actions.append(finished_call)
            else:
                # just record the generic error, probably its out of gas or something
                self.call_stack.append(self.call_stack.pop()._replace(
                    is_error=True,
                    error=str(e),
                ))

    def post_transaction_hook(self, vm: VM, receipt: ReceiptAPI, computation: ComputationAPI):
        assert len(self.call_stack) == 1, f'expected {len(self.call_stack)} == 1'

        self.root_call = self.call_stack[0]._replace(
            returndata=computation.output,
            is_error=computation.is_error,
            gas_used=receipt.gas_used,
        )

    def pretty_print_calltrace(self):
        def _pretty_print_calltrace(call: TracedCall, indent: int):
            print('  ' * indent, end='')
            print(f'#{call.id} {call.call_type} {call.callee.hex()} {call.value} {call.calldata.hex()}')
            for action in call.actions:
                _pretty_print_calltrace(action, indent+1)
        _pretty_print_calltrace(self.root_call, 0)