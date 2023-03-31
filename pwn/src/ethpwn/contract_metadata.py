from collections import defaultdict
from contextlib import contextmanager
import json
import os
from pathlib import Path
from time import sleep
from typing import Any, Dict, Generator, List, Tuple, Union
from hexbytes import HexBytes
from solcx import compile_standard
from web3.types import TxReceipt
from web3.contract import Contract
import solcx
from ansi.color.fx import reset, bold, faint as dim
from ansi.color.fg import red, green, yellow, blue, magenta, cyan

from .serialization_utils import serialize_to_file, deserialize_from_file, Serializable

from .config.wallets import get_wallet_by_address, Wallet
from .config import get_contract_registry_dir, get_logged_deployed_contracts_dir
from .transactions import transact
from .global_context import context
from .hashes import lookup_signature_hash, register_signature_hash, signature_hash
from .srcmap import SymbolizedSourceMap, InstructionSourceInfo
from .pyevmasm_fixed import disassemble_all, Instruction

def read_sources(sources):
    sources_by_id = {}
    for file, v in sources.items():
        with open(file, 'r') as f:
            sources_by_id[v['id']] = {
                'id': v['id'],
                'path': os.path.abspath(file),
                'content': f.read(),
            }
    return sources_by_id

class ContractMetadata(Serializable):
    def __init__(self,
                    source_file=None,
                    sources_by_id=None,
                    contract_name=None,
                    abi=None,
                    bin=None,
                    bin_runtime=None,
                    srcmap=None,
                    srcmap_runtime=None,
                    **kwargs
                 ) -> None:
        super().__init__()
        self.source_file = source_file
        self.sources_by_id = sources_by_id
        self.contract_name = contract_name
        self.abi = abi
        self.bin = bin
        self.bin_runtime = bin_runtime
        self.srcmap = srcmap
        self.srcmap_runtime = srcmap_runtime
        self._symbolic_srcmap_constructor: SymbolizedSourceMap = None
        self._symbolic_srcmap_runtime: SymbolizedSourceMap = None
        self._disass_instructions: List[Instruction] = None
        self._disass_instructions_runtime: List[Instruction] = None

    def from_solidity(source_file, contract_name, json_dict, sources):
        source_file = str(Path(source_file).resolve())
        sources_by_id = read_sources(sources)
        abi = json_dict['abi']
        bin = HexBytes(json_dict['evm']['bytecode']['object'])
        bin_runtime = HexBytes(json_dict['evm']['deployedBytecode']['object'])
        srcmap = json_dict['evm']['bytecode']['sourceMap']
        srcmap_runtime = json_dict['evm']['deployedBytecode']['sourceMap']

        return ContractMetadata(
            source_file=source_file,
            contract_name=contract_name,
            sources_by_id=sources_by_id,
            abi=abi,
            bin=bin,
            bin_runtime=bin_runtime,
            srcmap=srcmap,
            srcmap_runtime=srcmap_runtime,
        )

    # implement the Serializable interface
    def to_serializable(self):
        # dump file_name, contract_name, and json_dict
        return {
            'source_file': str(self.source_file),
            'contract_name': self.contract_name,
            'sources_by_id': self.sources_by_id,
            'abi': self.abi,
            'bin': self.bin,
            'bin-runtime': self.bin_runtime,
            'srcmap': self.srcmap,
            'srcmap-runtime': self.srcmap_runtime,
        }

    @staticmethod
    def from_serializable(data):
        return ContractMetadata(
            source_file=data['source_file'],
            contract_name=data['contract_name'],
            sources_by_id={int(k): v for k, v in data['sources_by_id'].items()},
            abi=data['abi'],
            bin=data['bin'],
            bin_runtime=data['bin-runtime'],
            srcmap=data['srcmap'],
            srcmap_runtime=data['srcmap-runtime'],
        )

    def __eq__(self, other):
        return self.to_serializable() == other.to_serializable()

    @property
    def symbolic_srcmap_constructor(self):
        disassembled_instructions = self.disassembled_instructions
        if self._symbolic_srcmap_constructor is None:
            self._symbolic_srcmap_constructor = SymbolizedSourceMap.from_src_map(self.srcmap, self.sources)
        assert len(disassembled_instructions) > len(self._symbolic_srcmap_constructor.entries)
        return self._symbolic_srcmap_constructor

    @property
    def symbolic_srcmap_runtime(self):
        disassembled_instructions = self.disassembled_instructions_runtime
        if self._symbolic_srcmap_runtime is None:
            self._symbolic_srcmap_runtime = SymbolizedSourceMap.from_src_map(self.srcmap_runtime, self.sources_by_id)
        assert len(disassembled_instructions) > len(self._symbolic_srcmap_runtime.entries)
        return self._symbolic_srcmap_runtime

    def instruction_index_for_constructor_pc(self, pc) -> int:
        insns = [i for i, insn in enumerate(self.disassembled_instructions) if i.pc == pc]
        assert len(insns) <= 1
        return insns[0] if len(insns) == 1 else None

    def instruction_index_for_runtime_pc(self, pc) -> int:
        insns = [i for i, insn in enumerate(self.disassembled_instructions_runtime) if insn.pc == pc]
        assert len(insns) <= 1
        return insns[0] if len(insns) == 1 else None

    def instruction_for_constructor_pc(self, pc) -> Instruction:
        idx = self.instruction_index_for_runtime_pc(pc)
        if idx is None:
            return None
        return self.disassembled_instructions[idx]

    def instruction_for_runtime_pc(self, pc) -> Instruction:
        idx = self.instruction_index_for_runtime_pc(pc)
        if idx is None:
            return None
        return self.disassembled_instructions_runtime[idx]

    def source_info_for_constructor_pc(self, pc) -> InstructionSourceInfo:
        insn_idx = self.instruction_index_for_constructor_pc(pc)
        return self.symbolic_srcmap_constructor.get_source_info_for_instruction(insn_idx)

    def source_info_for_runtime_pc(self, pc) -> InstructionSourceInfo:
        insn_idx = self.instruction_index_for_runtime_pc(pc)
        return self.symbolic_srcmap_runtime.get_source_info_for_instruction(insn_idx)

    @property
    def disassembled_instructions_constructor(self) -> List[Instruction]:
        if self._disass_instructions is None:
            self._disass_instructions = list(disassemble_all(self.bin))
        return self._disass_instructions

    @property
    def disassembled_instructions_runtime(self):
        if self._disass_instructions_runtime is None:
            self._disass_instructions_runtime = list(disassemble_all(self.bin_runtime))
        return self._disass_instructions_runtime

    def deploy(self, *constructor_args, **tx_extras) -> Tuple[HexBytes, Contract]:
        from .contract_registry import register_deployed_contract
        tx_hash, tx_receipt = transact(
            context.w3.eth.contract(
                abi=self.abi,
                bytecode=self.bin
            ).constructor(*constructor_args),
            **tx_extras
        )

        address = tx_receipt['contractAddress']
        register_deployed_contract(self, address=address, deploy_tx_hash=tx_hash, deploy_tx_receipt=tx_receipt)
        return tx_hash, self.get_contract_at(address)

    @contextmanager
    def deploy_destructible(self, *constructor_args, **tx_extras):
        tx_hash, contract = self.deploy(*constructor_args, **tx_extras)
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
        from .contract_registry import register_contract_at_address
        register_contract_at_address(self, addr)
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
            for location in error.get('secondarySourceLocations', []):
                log(f"    {location['file']}:{location['start']}:{location['end']}: {location['message']}")
            if error['severity'] == 'error':
                compilation_error = True
        if compilation_error:
            raise Exception("Compilation error")

        for source_file in output_json['contracts']:
            for contract_name in output_json['contracts'][source_file]:
                contract_data = output_json['contracts'][source_file][contract_name]
                self.contract_info[source_file][contract_name] = ContractMetadata.from_solidity(
                    source_file, contract_name, contract_data, output_json['sources']
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
