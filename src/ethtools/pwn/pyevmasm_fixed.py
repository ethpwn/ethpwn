
from bisect import bisect
import functools
import pyevmasm

from pyevmasm import DEFAULT_FORK
DEFAULT_FORK = 'paris'

from pyevmasm.evmasm import instruction_tables, london_instruction_table, istanbul_instruction_table, accepted_forks, InstructionTable, Instruction


muir_glacier_instruction_table = InstructionTable({}, previous_fork=istanbul_instruction_table)

if 'muir-glacier' not in accepted_forks:
    accepted_forks += ('muir-glacier',)
if 'muir-glacier' not in instruction_tables:
    instruction_tables['muir-glacier'] = muir_glacier_instruction_table


paris_instruction_table = {0x44: ("PREVRANDAO", 0, 0, 1, 2, "Get the previous blocks Randao random number.")}

paris_instruction_table = InstructionTable(  # type: ignore
    paris_instruction_table, previous_fork=london_instruction_table
)
if 'paris' not in accepted_forks:
    accepted_forks += ('paris',)
if 'paris' not in instruction_tables:
    instruction_tables['paris'] = paris_instruction_table

def block_to_fork_fixed(block_number):
    forks_by_block = {
        0: "frontier",
        1150000: "homestead",
        # 1920000 Dao
        2463000: "tangerine_whistle",
        2675000: "spurious_dragon",
        4370000: "byzantium",
        # 7280000: "constantinople", # Same Block as petersburg, commented to avoid conflicts
        7280000: "petersburg",
        9069000: "istanbul",
        9200000: 'muir-glacier',
        12965000: "london",
        15537394: "paris",
        99999999: "serenity",  # to be replaced after Serenity launch
    }
    fork_names = list(forks_by_block.values())
    fork_blocks = list(forks_by_block.keys())
    return fork_names[bisect(fork_blocks, block_number) - 1]

pyevmasm.block_to_fork = block_to_fork_fixed



from pyevmasm import assemble, assemble_all, assemble_hex, assemble_one
from pyevmasm import disassemble_all as __disassemble_all_uncached
from pyevmasm import disassemble_one as __disassemble_one_uncached
from pyevmasm import disassemble_hex as __disassemble_hex_uncached
from pyevmasm import disassemble as __disassemble_uncached

@functools.lru_cache(maxsize=64, typed=True)
def disassemble_all(bytecode, pc=0, fork='paris'):
    return list(__disassemble_all_uncached(bytecode, pc, fork))

@functools.lru_cache(maxsize=64, typed=True)
def disassemble_one(bytecode, pc=0, fork='paris'):
    return __disassemble_one_uncached(bytecode, pc, fork)

@functools.lru_cache(maxsize=64, typed=True)
def disassemble_hex(bytecode, pc=0, fork='paris'):
    return __disassemble_hex_uncached(bytecode, pc, fork)

@functools.lru_cache(maxsize=64, typed=True)
def disassemble(bytecode, pc=0, fork='paris'):
    return __disassemble_uncached(bytecode, pc, fork)


