from collections import defaultdict
from contextlib import contextmanager
import json
import os
from pathlib import Path
from time import sleep
from typing import Any, Dict, Generator, Iterator, List, Optional, Tuple, Union
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
from .solcx_utils import SolidityCompiler, configure_solcx_for_pragma, find_pragma_line

def convert_sources(sources):
    sources_out = []
    for file, v in sources.items():
        with open(file, 'r') as f:
            abspath = Path(file).resolve()
            sources_out.append({
                'id': int(v['id']),
                'contents': f.read(),
                'full_path': str(abspath),
                'name': abspath.name,
                'language': 'Solidity',
                'generated': False,
            })
    return list(sorted(sources_out, key=lambda s: s['id']))


class ContractMetadata(Serializable):
    def __init__(self,
                    source_file=None,
                    contract_name=None,
                    sources_by_id=None,
                    generated_sources_by_id_constructor=None,
                    generated_sources_by_id_runtime=None,
                    abi=None,
                    bin=None,
                    bin_runtime=None,
                    srcmap=None,
                    srcmap_runtime=None,
                    storage_layout=None,
                    **kwargs
                 ) -> None:
        super().__init__()
        self.source_file = source_file
        self.contract_name = contract_name
        self.sources = sources_by_id
        self.generated_sources_constructor = generated_sources_by_id_constructor
        self.generated_sources_runtime = generated_sources_by_id_runtime
        self.abi = abi
        self.bin = bin
        self.bin_runtime = bin_runtime
        self.srcmap = srcmap
        self.srcmap_runtime = srcmap_runtime
        self.storage_layout = storage_layout
        self._symbolic_srcmap_constructor: SymbolizedSourceMap = None
        self._symbolic_srcmap_runtime: SymbolizedSourceMap = None
        self._disass_instructions: List[Instruction] = None
        self._disass_instructions_runtime: List[Instruction] = None

    def from_solidity(source_file, contract_name, json_dict, sources):
        source_file = str(Path(source_file).resolve())
        sources = convert_sources(sources)
        # import ipdb; ipdb.set_trace()
        abi = json_dict['abi']
        bin = HexBytes(json_dict['evm']['bytecode']['object'])
        bin_runtime = HexBytes(json_dict['evm']['deployedBytecode']['object'])
        srcmap = json_dict['evm']['bytecode']['sourceMap']
        srcmap_runtime = json_dict['evm']['deployedBytecode']['sourceMap']
        generated_sources_constructor = json_dict['evm']['bytecode']['generatedSources']
        for src in generated_sources_constructor:
            del src['ast']
            src['generated'] = True
        generated_sources_runtime = json_dict['evm']['deployedBytecode']['generatedSources']
        for src in generated_sources_runtime:
            del src['ast']
            src['generated'] = True
        storage_layout = json_dict['storageLayout']

        return ContractMetadata(
            source_file=source_file,
            contract_name=contract_name,
            sources_by_id=sources,
            generated_sources_by_id_constructor=generated_sources_constructor,
            generated_sources_by_id_runtime=generated_sources_runtime,
            abi=abi,
            bin=bin,
            bin_runtime=bin_runtime,
            srcmap=srcmap,
            srcmap_runtime=srcmap_runtime,
            storage_layout=storage_layout,
        )

    # implement the Serializable interface
    def to_serializable(self):
        # dump file_name, contract_name, and json_dict
        return {
            'source_file': str(self.source_file),
            'contract_name': self.contract_name,
            'sources': self.sources,
            'generated_sources_constructor': self.generated_sources_constructor,
            'generated_sources_runtime': self.generated_sources_runtime,
            'abi': self.abi,
            'bin': self.bin,
            'bin-runtime': self.bin_runtime,
            'srcmap': self.srcmap,
            'srcmap-runtime': self.srcmap_runtime,
            'storage-layout': self.storage_layout,
        }

    @staticmethod
    def from_serializable(data):
        return ContractMetadata(
            source_file=data['source_file'],
            contract_name=data['contract_name'],
            sources_by_id=data['sources'],
            generated_sources_by_id_constructor=data['generated_sources_constructor'],
            generated_sources_by_id_runtime=data['generated_sources_runtime'],
            abi=data['abi'],
            bin=data['bin'],
            bin_runtime=data['bin-runtime'],
            srcmap=data['srcmap'],
            srcmap_runtime=data['srcmap-runtime'],
            storage_layout=data['storage-layout'],
        )


    def constructor_source_by_id(self, id):
        for source in self.sources + self.generated_sources_constructor:
            if source['id'] == id:
                return source

        raise Exception(f"Unknown source id {id}")

    def runtime_source_by_id(self, id):
        for source in self.sources + self.generated_sources_runtime:
            if source['id'] == id:
                return source

        raise Exception(f"Unknown source id {id}")

    def __eq__(self, other):
        return self.to_serializable() == other.to_serializable()

    @property
    def symbolic_srcmap_constructor(self):
        if self._symbolic_srcmap_constructor is None:
            self._symbolic_srcmap_constructor = SymbolizedSourceMap.from_src_map(self.srcmap, self.constructor_source_by_id)
        return self._symbolic_srcmap_constructor

    @property
    def symbolic_srcmap_runtime(self):
        if self._symbolic_srcmap_runtime is None:
            self._symbolic_srcmap_runtime = SymbolizedSourceMap.from_src_map(self.srcmap_runtime, self.runtime_source_by_id)
        return self._symbolic_srcmap_runtime

    def closest_instruction_index_for_constructor_pc(self, pc, fork='paris') -> int:
        disass = disassemble_all(self.bin, pc=0, fork=fork)
        insns = [i for i, insn in enumerate(disass) if i.pc <= pc]
        # gets the closest instruction that is before the pc
        return insns[-1] if len(insns) >= 1 else None

    def closest_instruction_index_for_runtime_pc(self, pc, fork='paris') -> int:
        disass = disassemble_all(self.bin_runtime, pc=0, fork=fork)
        insns = [i for i, insn in enumerate(disass) if insn.pc <= pc]
        # gets the closest instruction that is before the pc
        return insns[-1] if len(insns) >= 1 else None

    def source_info_for_constructor_instruction_idx(self, insn_idx) -> InstructionSourceInfo:
        return self.symbolic_srcmap_constructor.get_source_info_for_instruction(insn_idx)

    def source_info_for_runtime_instruction_idx(self, insn_idx) -> InstructionSourceInfo:
        return self.symbolic_srcmap_runtime.get_source_info_for_instruction(insn_idx)

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
        self.compiler: SolidityCompiler = SolidityCompiler()
        self.compiler.add_import_remappings({
            "exploit_templates": exp_template_dir,
        })

    def add_solidity_source(self, source: str, file_name: Union[Path, str], **kwargs):
        self.process_solc_output_json(self.compiler.compile_source(source, file_name, **kwargs))

    def add_solidity_files(self, files: List[Union[str, Path]], **kwargs):
        self.process_solc_output_json(self.compiler.compile_files(files, **kwargs))

    def handle_solidity_errors(self, output_json):
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

    def process_solc_output_json(self, output_json):

        self.handle_solidity_errors(output_json)

        for source_file in output_json['contracts']:
            for contract_name in output_json['contracts'][source_file]:
                contract_data = output_json['contracts'][source_file][contract_name]
                self.contract_info[source_file][contract_name] = ContractMetadata.from_solidity(
                    source_file, contract_name, contract_data, output_json['sources']
                )
                self.contract_info[''][contract_name] = self.contract_info[source_file][contract_name]

                # ensure these can actually get built
                self.contract_info[''][contract_name].symbolic_srcmap_constructor
                self.contract_info[''][contract_name].symbolic_srcmap_runtime


    # make it so that metadata_registry['name'] returns the metadata for the contract of that name, and metadata_registry[('file', 'name')] returns the metadata for the contract of that name in that file
    def __getitem__(self, key: Union[str, Tuple[str, str]]) -> ContractMetadata:
        if isinstance(key, tuple):
            return self.contract_info[key[0]][key[1]]
        else:
            return self.contract_info[''][key]
    def __contains__(self, key: Union[str, Tuple[str, str]]) -> bool:
        if isinstance(key, tuple):
            return key[1] in self.contract_info[key[0]]
        else:
            return key in self.contract_info['']

    def __iter__(self):
        return self.all_contracts()

    def iter_find(self, predicate) -> Iterator[Tuple[str, str, ContractMetadata]]:
        for file_name, file_data in self.contract_info.items():
            for contract_name, contract_data in file_data.items():
                if predicate(file_name, contract_name, contract_data):
                    yield file_name, contract_name, contract_data

    def find(self, predicate) -> Optional[Tuple[str, str, ContractMetadata]]:
        return next(self.iter_find(predicate), None)

    def iter_find_by_name(self, name: str) -> Iterator[Tuple[str, str, ContractMetadata]]:
        return self.iter_find(lambda file_name, contract_name, contract_data: contract_name == name)

    def find_by_name(self, name: str) -> Optional[Tuple[str, str, ContractMetadata]]:
        return self.find(lambda file_name, contract_name, contract_data: contract_name == name)

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
