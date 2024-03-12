
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

def calculate_create_contract_address(w3, sender_address, nonce):
    from rlp import encode as rlp_encode
    arg1 = sender_address
    arg2 = nonce
    args_encoded = rlp_encode([sender_address, nonce])
    b_result = w3.keccak(args_encoded)
    contract_address = w3.to_checksum_address(b_result[12:].hex())
    return contract_address

def calculate_create2_contract_address(w3, sender_address, salt, init_code_bytes):
    # Convert the sender address to bytes
    pre = '0xff'
    arg1 = bytes.fromhex(pre[2:])
    arg2 = sender_address
    arg3 = salt
    arg4 = init_code_bytes

    keccak_b_code = w3.keccak(arg4)
    b_result = w3.keccak(arg1+arg2+arg3+keccak_b_code)
    contract_address = w3.to_checksum_address(b_result[12:].hex())
    return contract_address