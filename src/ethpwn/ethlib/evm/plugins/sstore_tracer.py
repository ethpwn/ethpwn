
import typing
from .base import *

class TracedSSTORE(typing.NamedTuple):
    id: int
    pc: int
    slot: bytes
    value: bytes
    old_value: bytes


class SStoreTracer(BaseAnalysisPlugin):
    PRE_OPERATION_PRIORITY: typing.ClassVar[int] = 90

    traced_sstores = []
    next_store_id: int
    name = "sstore_tracer"

    def pre_transaction_hook(self, vm: VM, txn: SignedTransactionMethods):
        self.next_store_id = 1

    def pre_opcode_hook(self, opcode: Opcode, computation: ComputationAPI):
        if opcode.mnemonic == 'SSTORE':
            # we want to remember SSTOREs
            (value_type, value), (slot_type, slot) = computation._stack.values[-2:]
            if slot_type == int:
                slot = int.to_bytes(slot, 32, byteorder='big', signed=False)
            if value_type == int:
                value = int.to_bytes(value, 32, byteorder='big', signed=False)

            slot = slot.rjust(32, b'\x00')
            value = value.rjust(32, b'\x00')
            old_value = computation.state.get_storage(
                computation.msg.storage_address,
                int.from_bytes(slot, byteorder='big', signed=False)
            ).to_bytes(length=32, byteorder='big', signed=False)

            self.traced_sstores.append(TracedSSTORE(
                id=self.next_store_id,
                pc=computation.code.program_counter,
                slot=slot,
                value=value,
                old_value=old_value,
            ))
            self.next_store_id += 1
