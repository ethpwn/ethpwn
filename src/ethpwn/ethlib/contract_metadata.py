'''
Module for everything to do with the contract metadata we have available.
Contains the metadata registry which is our knowledge base of all the contracts
we know about, and the `ContractMetadata` class which describes and holds that
metadata for a single contract.
'''

from collections import defaultdict
from contextlib import contextmanager
import os
from pathlib import Path
from time import sleep
from typing import Dict, Iterator, List, Literal, Optional, Tuple, Union
from hexbytes import HexBytes
from web3.contract import Contract
from ansi.color.fx import reset, bold
from ansi.color.fg import red
from rich.tree import Tree
from rich.table import Table

from ethpwn.ethlib.compilation.compiler_vyper import VyperCompiler

from .serialization_utils import Serializable
from .transactions import transact
from .global_context import context

from .config.misc import should_log_compiler_message
from .compilation.srcmap import SymbolizedSourceMap, InstructionSourceInfo
from .compilation.compiler_solidity import SolidityCompiler
from .compilation.compiler_vyper import VyperCompiler

from pyevmasm import disassemble_all, Instruction

def get_language_for_compiler(compiler):
    '''
    Extract a language identifier from a given compiler json_output['compiler'] string.
    '''
    if compiler.startswith('vyper-'):
        return 'Vyper'
    else:
        assert compiler.startswith('solc-')
        return 'Solidity'

def _unify_sources(compiler, input_sources, output_sources):
    '''
    Unifies the input and output sources into a single list of sources with the same format
    as the output sources. This ensures that all sources with their corresponding content
    are present in the JSON output by reading them from their respective source files into
    memory. This way, we can be sure that the source code is always available in the output
    and does not change after the fact.
    '''
    # import ipdb; ipdb.set_trace()
    assert input_sources.keys() == output_sources.keys()
    sources_out = []
    for file, values in output_sources.items():
        result = {
            'id': int(values['id']),
            'name': file,
            'file_name': os.path.basename(file),
            'language': get_language_for_compiler(compiler),
            'generated': False,
        }
        if input_sources[file]['content'] is None:
            with open(file, 'r', encoding='utf-8') as file_obj:
                result['content'] = file_obj.read()
            result['local_path'] = Path(file).resolve()
        else:
            result['content'] = input_sources[file]['content']
            result['local_path'] = None
        result['contents'] = result['content']
        sources_out.append(result)
    return list(sorted(sources_out, key=lambda s: s['id']))

class ContractMetadata(Serializable):
    '''
    Holds all of the available metadata about a contract.
    Includes the ABI, the bytecode, the source code, and the source map.
    '''
    def __init__(self,
                    compiler=None,
                    source_file=None,
                    contract_name=None,
                    sources_by_id=None,
                    generated_sources_by_id_constructor=None,
                    generated_sources_by_id_runtime=None,
                    abi=None,
                    # pylint: disable=redefined-builtin
                    bin=None,
                    bin_runtime=None,
                    srcmap=None,
                    srcmap_runtime=None,
                    storage_layout=None,
                 ) -> None:
        super().__init__()

        assert compiler is not None
        self.compiler = compiler
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

    def _rich_table_for_abi(self, _console, _options):
        table = Table(title="ABI functions")
        table.add_column("Type")
        table.add_column("Name")
        table.add_column("Mutability")
        table.add_column("Inputs")
        table.add_column("Outputs")
        for entry in self.abi:
            table.add_row(
                entry.get('type', None),
                entry.get('name', None),
                entry.get('stateMutability', None),
                ', '.join([f"{i['type']} {i['name']}" for i in entry.get('inputs', [])]),
                ', '.join([f"{i['type']} {i['name']}" for i in entry.get('outputs', [])]),
            )
        return table

    def _rich_table_for_storage_layout(self, _console, _options):
        table = Table(title="Storage layout")
        table.add_column("Type")
        table.add_column("Name")
        table.add_column("Offset")
        table.add_column("Slot")
        table.add_column("Size")
        table.add_column("Encoding")
        types = self.storage_layout['types']
        for entry in self.storage_layout['storage']:
            resolved_type = types[entry['type']]
            table.add_row(
                resolved_type['label'],
                entry['label'],
                str(entry['offset']),
                str(entry['slot']),
                resolved_type['numberOfBytes'],
                resolved_type['encoding'],
            )
        return table

    def __rich_console__(self, console, options):

        tree = Tree("Metadata")
        tree.add(f"{bold(self.contract_name)} ({self.source_file})")
        abi = tree.add(f"{bold('ABI')}")
        abi.add(self._rich_table_for_abi(console, options))

        if self.bin is not None:
            tree.add(f"{bold('Bytecode (constructor)')}")
        if self.bin_runtime is not None:
            tree.add(f"{bold('Bytecode (runtime)')}")

        storage_layout = tree.add(f"{bold('Storage Layout')}")
        storage_layout.add(self._rich_table_for_storage_layout(console, options))

        if self._symbolic_srcmap_constructor:
            tree.add(f"{bold('Source Map (constructor)')}")
        if self._symbolic_srcmap_runtime:
            tree.add(f"{bold('Source Map (runtime)')}")

        yield tree

    @staticmethod
    def from_compiler_output_json(compiler, source_file, contract_name, output_json, input_sources, output_sources):
        '''
        Constructs a ContractMetadata object for a contract in `source_file` with
        name `contract_name` from the Compiler `output_json` and the `sources` dict.
        '''
        # import ipdb; ipdb.set_trace()
        source_file = str(Path(source_file).resolve())
        sources = _unify_sources(compiler, input_sources, output_sources)
        # import ipdb; ipdb.set_trace()
        abi = output_json['abi']
        bin_constructor = HexBytes(output_json['evm']['bytecode']['object'])
        bin_runtime = HexBytes(output_json['evm']['deployedBytecode']['object'])
        srcmap = output_json['evm']['bytecode'].get('sourceMap', None)              # vyper contracts don't have this for the constructor
        srcmap_runtime = output_json['evm']['deployedBytecode']['sourceMap']
        generated_sources_constructor = output_json['evm']['bytecode'].get('generatedSources', [])
        for src in generated_sources_constructor:
            del src['ast']
            src['generated'] = True
        generated_sources_runtime = output_json['evm']['deployedBytecode'].get('generatedSources', [])
        for src in generated_sources_runtime:
            del src['ast']
            src['generated'] = True
        storage_layout = output_json.get('storageLayout', {'types': [], 'storage': []})

        return ContractMetadata(
            compiler,
            source_file=source_file,
            contract_name=contract_name,
            sources_by_id=sources,
            generated_sources_by_id_constructor=generated_sources_constructor,
            generated_sources_by_id_runtime=generated_sources_runtime,
            abi=abi,
            bin=bin_constructor,
            bin_runtime=bin_runtime,
            srcmap=srcmap,
            srcmap_runtime=srcmap_runtime,
            storage_layout=storage_layout,
        )

    # implement the Serializable interface
    def to_serializable(self):
        '''
        Returns a serializable dictionary representation of the object.
        '''
        # dump file_name, contract_name, and json_dict
        return {
            'compiler': self.compiler,
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
    def from_serializable(value):
        '''
        Loads a ContractMetadata object back from a serialized dictionary.
        '''
        return ContractMetadata(
            compiler=value['compiler'],
            source_file=value['source_file'],
            contract_name=value['contract_name'],
            sources_by_id=value['sources'],
            generated_sources_by_id_constructor=value['generated_sources_constructor'],
            generated_sources_by_id_runtime=value['generated_sources_runtime'],
            abi=value['abi'],
            bin=value['bin'],
            bin_runtime=value['bin-runtime'],
            srcmap=value['srcmap'],
            srcmap_runtime=value['srcmap-runtime'],
            storage_layout=value['storage-layout'],
        )

    @property
    def language(self) -> Union[Literal['vyper'], Literal['solidity']]:
        '''
        Based on the `compiler` property, return the language the given contract was written in.
        Currently supports `vyper` and `solidity`.
        '''
        if self.compiler.startswith('vyper-'):
            return 'vyper'
        else:
            assert self.compiler.startswith('solc-')
            return 'solidity'

    @property
    def compiler_name(self) -> Union[Literal['vyper'], Literal['solc']]:
        '''
        Based on the `compiler` property, return the name of the compiler used to compile the
        contract. Currently supports `vyper` and `solc`. Does not include version/commit information.
        '''
        if self.compiler.startswith('vyper-'):
            return 'vyper'
        else:
            assert self.compiler.startswith('solc-')
            return 'solc'

    def constructor_source_by_id(self, _id):
        '''
        Looks up and returns the source code object for the given source id in the constructor code.
        '''
        for source in self.sources + self.generated_sources_constructor:
            if source['id'] == _id:
                return source

        raise ValueError(f"Unknown source id {_id}")

    def runtime_source_by_id(self, _id):
        '''
        Looks up and returns the source code object for the given source id in the runtime code.
        '''
        for source in self.sources + self.generated_sources_runtime:
            if source['id'] == _id:
                return source

        raise ValueError(f"Unknown source id {_id}")

    def __eq__(self, other):
        return self.to_serializable() == other.to_serializable()

    @property
    def symbolic_srcmap_constructor(self):
        '''
        Returns the symbolized source map for the constructor bytecode.
        '''
        if self._symbolic_srcmap_constructor is None and self.srcmap is not None:
            self._symbolic_srcmap_constructor = SymbolizedSourceMap.from_src_map(
                self.srcmap, self.constructor_source_by_id
            )
        return self._symbolic_srcmap_constructor

    @property
    def symbolic_srcmap_runtime(self):
        '''
        Returns the symbolized source map for the runtime bytecode.
        '''
        if self._symbolic_srcmap_runtime is None and self.srcmap_runtime is not None:
            self._symbolic_srcmap_runtime = SymbolizedSourceMap.from_src_map(
                self.srcmap_runtime, self.runtime_source_by_id
            )
        return self._symbolic_srcmap_runtime

    # pylint: disable=invalid-name
    def closest_instruction_index_for_constructor_pc(self,
                                                     pc, fork='paris'
                                                     ) -> int:
        '''
        Returns the index of the closest instruction in the constructor bytecode that is before
        or at the given pc in the constructor bytecode.
        '''
        disass = disassemble_all(self.bin, pc=0, fork=fork)
        insns = [i for i, insn in enumerate(disass) if i.pc <= pc]
        # gets the closest instruction that is before the pc
        return insns[-1] if len(insns) >= 1 else None

    def closest_instruction_index_for_runtime_pc(self, pc, fork='paris') -> int:
        '''
        Returns the index of the closest instruction in the runtime bytecode that is before or at
        the given pc in the runtime bytecode.
        '''
        disass = disassemble_all(self.bin_runtime, pc=0, fork=fork)
        insns = [i for i, insn in enumerate(disass) if insn.pc <= pc]
        # gets the closest instruction that is before the pc
        return insns[-1] if len(insns) >= 1 else None

    def source_info_for_constructor_instruction_idx(self, insn_idx) -> InstructionSourceInfo:
        '''
        Returns the source info for instruction at index `insn_idx` in the constructor bytecode.
        '''
        return self.symbolic_srcmap_constructor.get_source_info_for_instruction(insn_idx)

    def source_info_for_runtime_instruction_idx(self, insn_idx) -> InstructionSourceInfo:
        '''
        Returns the source info for instruction at index `insn_idx` in the runtime bytecode.
        '''
        return self.symbolic_srcmap_runtime.get_source_info_for_instruction(insn_idx)

    def deploy(self, *constructor_args, **tx_extras) -> Tuple[HexBytes, Contract]:
        '''
        Deploys a contract and registers it with the contract registry.
        '''
        # pylint: disable=import-outside-toplevel
        from .contract_registry import register_deployed_contract
        tx_hash, tx_receipt = transact(
            context.w3.eth.contract(
                abi=self.abi,
                bytecode=self.bin
            ).constructor(*constructor_args),
            **tx_extras
        )

        address = tx_receipt['contractAddress']
        register_deployed_contract(self,
                                   address=address,
                                   deploy_tx_hash=tx_hash,
                                   deploy_tx_receipt=tx_receipt
                                   )

        return tx_hash, self.get_contract_at(address)

    @contextmanager
    def deploy_destructible(self, *constructor_args, **tx_extras):
        '''
        Deploys a `Destructible` contract and `destroy()`s it after the context manager exits
        to retrieve any held funds. Utility function for quick one-off contracts so you can
        easily get your funds back by default. The resulting deployed contract will also be
        automatically registered with the contract registry.
        '''
        tx_hash, contract = self.deploy(*constructor_args, **tx_extras)
        exception = None
        try:
            yield tx_hash, contract
        except Exception as exc:
            exception = exc
            raise
        finally:
            sleep(2)
            if exception:
                context.logger.exception("Encountered exception: %s", exception)
            context.logger.info("Destroying contract %s to get funds back!", contract.address)
            transact(contract.functions.destroy(), from_addr=tx_extras.get('from_addr', None))

    def get_contract_at(self, addr) -> Contract:
        '''
        Returns a web3 contract instance for the contract at the given address. This will
        automatically register the contract at the given address with the contract registry.
        '''
        # pylint: disable=import-outside-toplevel
        from .contract_registry import register_contract_at_address
        register_contract_at_address(self, addr)
        return context.w3.eth.contract(
            address=addr,
            abi=self.abi
        )

    def decode_function_input(self, data):
        '''
        Decodes the function input data for a contract of this class. Returns a tuple of the
        function name and a dictionary of the arguments.
        '''
        contract = context.w3.eth.contract(abi=self.abi)
        return contract.decode_function_input(data)


class ContractMetadataRegistry:
    '''
    A registry containing all contracts and metadata for them that we know about. This is used
    to retrieve information about deployed contracts, associate new contracts with their metadata,
    and to retrieve metadata for contracts that are not deployed yet. This is the central point
    for all contract-related metadata.
    '''
    def __init__(self) -> None:
        self.contracts: Dict[str, Dict[str, ContractMetadata]] = defaultdict(dict)
        exp_template_dir = os.path.dirname(os.path.realpath(__file__)) + "/exploit_templates"
        self.solidity_compiler: SolidityCompiler = SolidityCompiler()
        self.solidity_compiler.add_import_remappings({
            "exploit_templates": exp_template_dir,
        })
        self.vyper_compiler: VyperCompiler = VyperCompiler()

    def add_source(self, source: str, file_name: Union[Path, str], compiler: str = None, **kwargs):
        result = None
        if compiler == 'vyper':
            result = self.vyper_compiler.compile_source(source, file_name, **kwargs)
        else:
            assert compiler == 'solc' or compiler is None
            result = self.solidity_compiler.compile_source(source, file_name, **kwargs)
        self._process_compiler_output_json(result)

    def add_sources_dict(self, sources: Dict[str, str], compiler: str = None, **kwargs):
        result = None
        if compiler == 'vyper':
            result = self.vyper_compiler.compile_sources(sources, **kwargs)
        else:
            assert compiler == 'solc' or compiler is None
            result = self.solidity_compiler.compile_sources(sources, **kwargs)
        self._process_compiler_output_json(result)

    def add_standard_json(self, input_json: Dict, compiler: str = None, **kwargs):
        result = None
        if compiler == 'vyper':
            result = self.vyper_compiler.compile_json(input_json, **kwargs)
        else:
            assert compiler == 'solc' or compiler is None
            result = self.solidity_compiler.compile_json(input_json, **kwargs)
        self._process_compiler_output_json(result)

    def add_files(self, files: List[Union[str, Path]], compiler: str = None, **kwargs):
        result = None
        if compiler == 'vyper':
            result = self.vyper_compiler.compile_files(files, **kwargs)
        else:
            assert compiler == 'solc' or compiler is None
            result = self.solidity_compiler.compile_files(files, **kwargs)
        self._process_compiler_output_json(result)


    def add_solidity_source(self, source: str, file_name: Union[Path, str], **kwargs):
        '''
        Compiles the given solidity source code and adds the resulting metadata
        of all contracts to the registry.
        '''
        self._process_compiler_output_json(self.solidity_compiler.compile_source(source, file_name, **kwargs))

    def add_solidity_sources_dict(self, sources: Dict[str, str], **kwargs):
        '''
        Compiles the given solidity source dict `'sources'` in the input json and adds the
        resulting metadata of all contracts to the registry.
        '''
        self._process_compiler_output_json(self.solidity_compiler.compile_sources(sources, **kwargs))

    def add_contracts_from_solidity_files(self, files: List[Union[str, Path]], **kwargs):
        '''
        Compiles the given files and adds the resulting metadata of all contracts to the registry.
        '''
        self._process_compiler_output_json(self.solidity_compiler.compile_files(files, **kwargs))

    def add_vyper_source(self, source: str, file_name: Union[Path, str], **kwargs):
        '''
        Compiles the given vyper source code and adds the resulting metadata
        of all contracts to the registry.
        '''
        self._process_compiler_output_json(self.vyper_compiler.compile_source(source, file_name, **kwargs))

    def add_vyper_sources_dict(self, sources: Dict[str, str], **kwargs):
        '''
        Compiles the given vyper source dict `'sources'` in the input json and adds the
        resulting metadata of all contracts to the registry.
        '''
        self._process_compiler_output_json(self.vyper_compiler.compile_sources(sources, **kwargs))

    def add_contracts_from_vyper_files(self, files: List[Union[str, Path]], **kwargs):
        '''
        Compiles the given files and adds the resulting metadata of all contracts to the registry.
        '''
        self._process_compiler_output_json(self.vyper_compiler.compile_files(files, **kwargs))

    # pylint: disable=line-too-long
    def _handle_errors(self, output_json):
        '''
        Handles errors in the compiler JSON output by printing them to the logger and raising an exception if
        compilation failed.
        '''
        compilation_error = False
        for error in output_json.get('errors', []):
            if should_log_compiler_message(error['severity']):
                log = getattr(context.logger, error['severity'], context.logger.info)
                # import ipdb; ipdb.set_trace()
                log(f"# {red}{bold}{error['severity'].upper()}:{error['type']} {error['formattedMessage']}{reset}")
                for location in error.get('secondarySourceLocations', []):
                    log(f"    {location['file']}:{location['start']}:{location['end']}: {location['message']}")
            if error['severity'] == 'error':
                compilation_error = True
        if compilation_error:
            raise ValueError("Compilation error")

    def _process_compiler_output_json(self, result):
        '''
        Parses out the metadata from the compiler output JSON and adds it to the `contracts` we know about.
        '''

        input_json, output_json = result

        self._handle_errors(output_json)

        for source_file in output_json['contracts']:
            for contract_name in output_json['contracts'][source_file]:
                contract_data = output_json['contracts'][source_file][contract_name]
                self.contracts[source_file][contract_name] = ContractMetadata.from_compiler_output_json(
                    output_json['compiler'],
                    source_file, contract_name,
                    contract_data,
                    input_json['sources'], output_json['sources']
                )
                self.contracts[''][contract_name] = self.contracts[source_file][contract_name]

                # ensure these can actually get built

                # pylint: disable=pointless-statement
                self.contracts[''][contract_name].symbolic_srcmap_constructor
                # pylint: disable=pointless-statement
                self.contracts[''][contract_name].symbolic_srcmap_runtime

    # make it so that metadata_registry['name'] returns the metadata for the contract of that name,
    # and metadata_registry[('file', 'name')] returns the metadata for the contract of that name
    # in that file
    def __getitem__(self, key: Union[str, Tuple[str, str]]) -> ContractMetadata:
        '''
        Retrieve a contract's metadata either by `name` or by `(file_name, contract_name)`.
        '''
        if isinstance(key, tuple):
            return self.contracts[key[0]][key[1]]
        else:
            return self.contracts[''][key]

    def __contains__(self, key: Union[str, Tuple[str, str]]) -> bool:
        '''
        Check if a contract's metadata is present either by `name` or by `(file_name, contract_name)`.
        '''
        if isinstance(key, tuple):
            return key[1] in self.contracts[key[0]]
        else:
            return key in self.contracts['']

    def __iter__(self):
        '''
        Iterate over all contracts, yielding the file name, contract name, and metadata for each.
        '''
        return self.all_contracts()

    def iter_find(self, predicate) -> Iterator[Tuple[str, str, ContractMetadata]]:
        '''
        Iterate over all contracts matching `predicate`, yielding the file name, contract name,
        and metadata for each.
        '''
        for file_name, file_data in self.contracts.items():
            for contract_name, contract_data in file_data.items():
                if predicate(file_name, contract_name, contract_data):
                    yield file_name, contract_name, contract_data

    def find(self, predicate) -> Optional[Tuple[str, str, ContractMetadata]]:
        '''
        Find the first contract matching `predicate`, returning the file name, contract name,
        and metadata.
        '''
        return next(self.iter_find(predicate), None)

    def iter_find_by_name(self, name: str) -> Iterator[Tuple[str, str, ContractMetadata]]:
        '''
        Iterate over all contracts with the given name, yielding the file name, contract name,
        and metadata for each.
        '''
        return self.iter_find(lambda file_name, contract_name, contract_data: contract_name == name)

    def find_by_name(self, name: str) -> Optional[Tuple[str, str, ContractMetadata]]:
        '''
        Find the first contract with the given name, returning the file name, contract name,
        and metadata.
        '''
        return self.find(lambda file_name, contract_name, contract_data: contract_name == name)

    def all_contracts(self):
        '''
        Iterate over all contracts, yielding the file name, contract name, and metadata for each.
        '''
        for file_name, file_data in self.contracts.items():
            for contract_name, contract_data in file_data.items():
                yield file_name, contract_name, contract_data

    # def save_to(self, path):
    #     import json
    #     for file_name, file_data in self.contract_info.items():
    #         with open(f'{path}/{file_name}.json', 'w') as f:
    #             for contract_name, contract_data in file_data.items():
    #                 withjson.dump(file_data, f,

CONTRACT_METADATA: ContractMetadataRegistry = ContractMetadataRegistry()
