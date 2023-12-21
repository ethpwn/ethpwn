
from eth.abc import ComputationAPI


def read_stack_int(computation: ComputationAPI, pos: int) -> int:
    """
    Read a value from the stack on the given computation, at the given position (1 = top)
    """
    val_type, val = computation._stack.values[-pos]
    if val_type == bytes:
        val = int.from_bytes(val, byteorder='big', signed=False)
    return val


def read_stack_bytes(computation, pos: int) -> int:
    """
    Read a value from the stack on the given computation, at the given position (1 = top)
    """
    val_type, val = computation._stack.values[-pos]
    if val_type == int:
        # convert val to bytes
        val = val.to_bytes(32,byteorder='big')
    return val