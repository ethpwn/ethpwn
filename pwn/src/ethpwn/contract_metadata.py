from collections import defaultdict
from contextlib import contextmanager
import json
import os
from time import sleep
from typing import Any, Dict, Generator, List, Tuple, Union
from hexbytes import HexBytes
from solcx import compile_standard
from web3.types import TxReceipt
from web3.contract import Contract
import solcx
from ansi.color.fx import reset, bold, faint as dim
from ansi.color.fg import red, green, yellow, blue, magenta, cyan

from .json_utils import json_dump, json_load

from .config.wallets import get_wallet_by_address, Wallet
from .config import get_contract_registry_dir, get_logged_deployed_contracts_dir
from .transactions import transact
from .global_context import context
from .hashes import lookup_signature_hash, register_signature_hash, signature_hash
from .srcmap import SymbolizedSourceMap
from .pyevmasm_fixed import disassemble_all, Instruction

def to_snake_case(s):
    s = s.replace('-', '_')
    return ''.join('_' + c.lower() if c.isupper() and i != 0 else c.lower() for i, c in enumerate(s)).lstrip('_')

def recursive_snake_case(d):
    if isinstance(d, dict):
        return {to_snake_case(k): recursive_snake_case(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [recursive_snake_case(v) for v in d]
    else:
        return d
# class SnakeCaseDict(dict):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.__dict__ = self

#     def __setitem__(self, key, value):
#         potential_keys = {to_snake_case(k) for k in self}
#         assert len(potential_keys) <= 1, f"Cannot have multiple keys with the same snake case representation: {potential_keys}"
#         if len(potential_keys) == 1:
#             key = potential_keys.pop()
#         super().__setitem__(key, value)

#     def __getitem__(self, key):
#         return super().__getitem__(to_snake_case(key))

#     def __delitem__(self, __key: _KT) -> None:
#         return super().__delitem__(to_snake_case(__key))

#     def __getattr__(self, key):
#         if key not in self:
#             raise AttributeError(f"SnakeCaseDict has no attribute {key}")
#         return self[key]

class ContractMetadata:
    def __init__(self, **kwargs) -> None:
        kwargs = recursive_snake_case(kwargs)
        self.source_file = kwargs.pop('source_file', None)
        self.contract_name = kwargs.pop('contract_name', None)
        self.sources = kwargs.pop('sources', None)
        self.info = kwargs
        self._symbolic_srcmap: SymbolizedSourceMap = None
        self._symbolic_srcmap_runtime: SymbolizedSourceMap = None
        self._disass_instructions: List[Instruction] = None
        self._disass_instructions_runtime: List[Instruction] = None

    def to_json_dict(self):
        # dump file_name, contract_name, and json_dict
        return {
            'source_file': self.source_file,
            'contract_name': self.contract_name,
            'sources': self.sources,\
            **self.info,
        }

    @property
    def creation_bytecode(self):
        return self.info['evm']['bytecode']['object']

    @property
    def runtime_bytecode(self):
        return self.info['evm']['deployed_bytecode']['object']

    @property
    def abi(self):
        return self.info['abi']

    @property
    def bin(self):
        return self.creation_bytecode

    @property
    def bin_runtime(self):
        return self.runtime_bytecode

    @property
    def srcmap(self):
        return self.info['evm']['bytecode']['source_map']

    @property
    def srcmap_runtime(self):
        return self.info['evm']['deployed_bytecode']['source_map']

    @property
    def symbolic_srcmap(self):
        disassembled_instructions = self.disassembled_instructions
        if self._symbolic_srcmap is None:
            self._symbolic_srcmap = SymbolizedSourceMap.from_src_map(self.srcmap, self.sources)
        assert len(disassembled_instructions) > len(self._symbolic_srcmap.entries)
        return self._symbolic_srcmap

    @property
    def symbolic_srcmap_runtime(self):
        disassembled_instructions = self.disassembled_instructions_runtime
        if self._symbolic_srcmap_runtime is None:
            self._symbolic_srcmap_runtime = SymbolizedSourceMap.from_src_map(self.srcmap_runtime, self.sources)
        assert len(disassembled_instructions) == len(self._symbolic_srcmap_runtime.entries)
        return self._symbolic_srcmap_runtime

    def instruction_for_pc(self, pc) -> Instruction:
        insns = [i for i in self.disassembled_instructions if i.pc == pc]
        assert len(insns) <= 1
        return insns[0] if len(insns) == 1 else None

    def runtime_instruction_for_pc(self, pc) -> Instruction:
        insns = [i for i in self.disassembled_instructions_runtime if i.pc == pc]
        assert len(insns) <= 1
        return insns[0] if len(insns) == 1 else None

    def instruction_index_for_pc(self, pc) -> int:
        return self.disassembled_instructions.index(self.instruction_for_pc(pc))

    def runtime_instruction_index_for_pc(self, pc) -> int:
        return self.disassembled_instructions_runtime.index(self.runtime_instruction_for_pc(pc))

    def source_for_pc(self, pc):
        insn_idx = self.instruction_index_for_pc(pc)
        return self.symbolic_srcmap.get_source_info_for_instruction(insn_idx)

    def runtime_source_for_pc(self, pc):
        insn_idx = self.runtime_instruction_index_for_pc(pc)
        return self.symbolic_srcmap_runtime.get_source_info_for_instruction(insn_idx)

    @property
    def disassembled_instructions(self) -> List[Instruction]:
        if self._disass_instructions is None:
            self._disass_instructions = list(disassemble_all(self.creation_bytecode))
        return self._disass_instructions

    @property
    def disassembled_instructions_runtime(self):
        if self._disass_instructions_runtime is None:
            self._disass_instructions_runtime = list(disassemble_all(self.runtime_bytecode))
        return self._disass_instructions_runtime

    def from_json_dict(d):
        return ContractMetadata(**d)

    def __getattr__(self, __name: str) -> Any:
        if __name in self.json_dict:
            return self.json_dict[__name]
        else:
            raise AttributeError(f"ContractMetadata has no attribute {__name}")

    def deploy(self, *constructor_args, log=True, **tx_extras) -> Tuple[HexBytes, Contract]:
        tx_hash, tx_receipt = transact(
            context.w3.eth.contract(
                abi=self.abi,
                bytecode=self.bin
            ).constructor(*constructor_args),
            **tx_extras
        )

        if log:
            log_deployed_contract(self, tx_hash, tx_receipt)

        address = tx_receipt['contractAddress']
        register_typed_contract(address, self)
        return tx_hash, self.get_contract_at(address)

    @contextmanager
    def deploy_destructible(self, *constructor_args, **tx_extras):
        tx_hash, contract = self.deploy(*constructor_args, log=False, **tx_extras)
        exception = None
        try:
            yield tx_hash, contract
        except Exception as e:
            exception = e
            raise
        finally:
            sleep(2)
            if exception:
                context.logger.info(f"Encountered exception: {exception}")
            context.logger.info(f"Destroying contract {contract.address} to get funds back!")
            transact(contract.functions.destroy(), from_addr=tx_extras.get('from_addr', None))

    def get_contract_at(self, addr) -> Contract:
        register_typed_contract(addr, self)
        return context.w3.eth.contract(
            address=addr,
            abi=self.abi
        )

    def decode_function_input(self, data):
        c = context.w3.eth.contract(abi=self.abi)
        return c.decode_function_input(data)


class ContractMetadataRegistry:
    def __init__(self) -> None:
        self.contract_info: Dict[str, Dict[str, ContractMetadata]] = defaultdict(dict)
        exp_template_dir = os.path.dirname(os.path.realpath(__file__)) + "/exploit_templates"
        self.default_import_remappings: Dict[str, str] = {
            "exploit_templates": exp_template_dir,
        }
        self.allowed_directories: List[str] = [exp_template_dir]

    def add_default_import_remappings(self, remappings: Dict[str, str]):
        self.default_import_remappings.update(remappings)
        self.add_allowed_directories(remappings.values())

    def add_allowed_directories(self, directories: List[str]):
        self.allowed_directories.extend(directories)

    def get_output_values(self):
        output_values = ['abi','bin','bin-runtime','asm','hashes','metadata','srcmap','srcmap-runtime']
        if solcx.get_solc_version().minor >= 6:
            output_values.append('storage-layout')
        return output_values

    def find_pragma_line(self, content: str):
        for line in content.splitlines():
            if line.strip().startswith('pragma solidity'):
                return line

    def get_pragma_lines(self, files: List[str]):
        pragma_lines = set()
        for file in files:
            with open(file, 'r') as f:
                solidity_pragma_line = self.find_pragma_line(f.read())
                if solidity_pragma_line is not None:
                    pragma_lines.add(solidity_pragma_line)
        return list(pragma_lines)

    def configure_solcx_for_pragma(self, pragma_line: str):
        if pragma_line is None:
            return

        solcx.install_solc_pragma(pragma_line)
        solcx.set_solc_version_pragma(pragma_line)

    def get_import_remappings(self, **kwargs):
        import_remappings = {} if kwargs.get('no_default_import_remappings', False) else self.default_import_remappings.copy()
        if 'import_remappings' in kwargs:
            import_remappings.update(kwargs.pop('import_remappings'))
        return import_remappings

    def get_allow_paths(self):
        return self.allowed_directories

    def get_solc_input_json(self, sources_entry, **kwargs):
        return {
            "language": "Solidity",
            'sources': sources_entry,
            'settings': {
                'remappings': [f'{key}={value}' for key, value in sorted(self.get_import_remappings(**kwargs).items())],
                'outputSelection': { "*": { "*": [ "*" ], "": [ "*" ] } },
            }
        }


    def add_solidity_source(self, source: str, file_name: str, **kwargs):

        self.configure_solcx_for_pragma(self.find_pragma_line(source))

        source = self.get_solc_input_json({file_name: {'content': source}}, **kwargs)

        output = compile_standard(
            source,
            allow_paths=self.get_allow_paths(),
            **kwargs
            )
        self.process_solc_output_json(output)

    def add_solidity_files(self, files: List[str], **kwargs):
        pragma_lines = self.get_pragma_lines(files)
        assert len(pragma_lines) <= 1, "Multiple solidity versions in files"
        self.configure_solcx_for_pragma(pragma_lines[0] if len(pragma_lines) == 1 else None)

        source = self.get_solc_input_json({
            path: {"urls": [path]} for path in files
        }, **kwargs)

        output = compile_standard(
            source,
            allow_paths=self.get_allow_paths() + [os.path.dirname(file) for file in files],
            **kwargs
            )
        self.process_solc_output_json(output)

    def process_solc_output_json(self, output_json):
        compilation_error = False
        for error in output_json.get('errors', []):
            log = getattr(context.logger, error['severity'], context.logger.info)
            log(f"# {red}{bold}{error['severity'].upper()}:{error['type']} {error['formattedMessage']}{reset}")
            for location in error['secondarySourceLocations']:
                log(f"    {location['file']}:{location['start']}:{location['end']}: {location['message']}")
            if error['severity'] == 'error':
                compilation_error = True
        if compilation_error:
            raise Exception("Compilation error")

        for source_file in output_json['contracts']:
            for contract_name in output_json['contracts'][source_file]:
                contract_data = output_json['contracts'][source_file][contract_name]
                self.contract_info[source_file][contract_name] = ContractMetadata(
                    source_file=source_file,
                    contract_name=contract_name,
                    sources=output_json['sources'],
                    **contract_data,
                )
                self.contract_info[''][contract_name] = self.contract_info[source_file][contract_name]


    # make it so that metadata_registry['name'] returns the metadata for the contract of that name, and metadata_registry[('file', 'name')] returns the metadata for the contract of that name in that file
    def __getitem__(self, key: Union[str, Tuple[str, str]]) -> ContractMetadata:
        if isinstance(key, tuple):
            return self.contract_info[key[0]][key[1]]
        else:
            return self.contract_info[''][key]

    def all_contracts(self):
        for file_name, file_data in self.contract_info.items():
            for contract_name, contract_data in file_data.items():
                yield file_name, contract_name, contract_data

    # def save_to(self, path):
    #     import json
    #     for file_name, file_data in self.contract_info.items():
    #         with open(f'{path}/{file_name}.json', 'w') as f:
    #             for contract_name, contract_data in file_data.items():
    #                 withjson.dump(file_data, f,

CONTRACT_METADATA: ContractMetadataRegistry = ContractMetadataRegistry()
