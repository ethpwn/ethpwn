
import typing

from .base import *

class TracedSLoad(typing.NamedTuple):
    id: int
    slot: bytes
    pc: int
    value: bytes

class SLoadTracer(BaseAnalysisPlugin):
    """
    Records all SLOAD actions done in a transaction.
    The loads are stored into the call tracer's action list.
    """
    PRE_OPERATION_PRIORITY: typing.ClassVar[int] = 90
    next_id: int
    traced_sloads = []
    name = "sload_tracer"

    def pre_transaction_hook(self, vm: VM, txn: SignedTransactionMethods):
        self.next_id = 1

    def pre_opcode_hook(self, opcode: Opcode, computation: ComputationAPI):
        if opcode.mnemonic == 'SLOAD':
            slot = read_stack_int(computation, 1)
            val = computation.state.get_storage(
                computation.msg.storage_address,
                slot
            ).to_bytes(length=32, byteorder='big', signed=False)
            self.traced_sloads.append(TracedSLoad(
                id = self.next_id,
                slot = slot.to_bytes(length=32, byteorder='big', signed=False),
                pc = computation.code.program_counter,
                value = val,
            ))
            self.next_id += 1


