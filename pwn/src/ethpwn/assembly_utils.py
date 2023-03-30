from hexbytes import HexBytes
from .pyevmasm_fixed import assemble, disassemble, disassemble_one, disassemble_all

def value_to_smallest_hexbytes(value):
    if type(value) is int:
        bit_length = value.bit_length()
        byte_length = (bit_length + 7) // 8
        if byte_length == 0:
            return HexBytes(b'\x00')
        return HexBytes(value.to_bytes(byte_length, 'big'))
    elif type(value) is HexBytes:
        return value
    else:
        raise ValueError('value must be int or HexBytes')

def asm_push_value(value):
    """Push value to the stack"""
    value = value_to_smallest_hexbytes(value)
    return assemble('PUSH' + str(len(value)) + ' ' + value.hex())

def asm_codecopy(dst, src, size):
    """Copy code from src to dst"""
    code = asm_push_value(size)
    code += asm_push_value(src)
    code += asm_push_value(dst)
    code += assemble('CODECOPY')
    return code

def asm_return(mem_offset, length):
    """Return a value from memory"""
    code = asm_push_value(length)
    code += asm_push_value(mem_offset)
    code += assemble('RETURN')
    return code

def asm_mstore(mem_offset, value):
    """Store value at key"""
    code = asm_push_value(value)
    code += asm_push_value(mem_offset)
    code += assemble('MSTORE')
    return code

def asm_mload(mem_offset):
    """Load value at key"""
    code = asm_push_value(mem_offset)
    code += assemble('MLOAD')
    return code

def asm_sstore(key, value):
    """Store value at key"""
    code = asm_push_value(value)
    code += asm_push_value(key)
    code += assemble('SSTORE')
    return code

def asm_sload(key):
    """Load value at key"""
    code = asm_push_value(key)
    code += assemble('SLOAD')
    return code

def create_shellcode_deployer_bin(shellcode):
    """Create a contract that deploys shellcode at a specific address"""
    shellcode = bytes(HexBytes(shellcode))

    return_code = asm_return(0, len(shellcode))

    prev_offset = 0

    while True:
        cur_offset = len(asm_codecopy(0, prev_offset, len(shellcode))) + len(return_code)
        if cur_offset > prev_offset:
            prev_offset = cur_offset
        else:
            break

    code = asm_codecopy(0, prev_offset, len(shellcode)) + return_code
    assert len(code) == prev_offset
    return HexBytes(code + shellcode)

def disassemble_pro(code, start_pc=0, fork='paris'):
    code = HexBytes(code)

    insns = disassemble_all(code, pc=start_pc, fork=fork)

    disassembly = ''
    for insn in insns:
        bytes_insn = code[insn.pc - start_pc:insn.pc + - start_pc + len(insn.bytes)]
        bytes_repr = ' '.join([f'{b:02x}' for b in bytes_insn])
        disassembly += f'{insn.pc:04x}: {bytes_repr:12} {str(insn):20} [gas={insn.fee}, description="{insn.description}"]\n'

    return disassembly

