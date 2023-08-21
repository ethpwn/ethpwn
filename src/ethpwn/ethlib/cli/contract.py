'''
Helpful functions available in the CLI.
'''

import argparse
import functools
import os
import ethcx
from typing import Dict, List
from hexbytes import HexBytes

from rich.table import Table

from ..compilation.compiler_solidity import try_match_optimizer_settings
from ..contract_names import contract_names, name_for_contract, register_contract_name, names_for_contract, contract_by_name
from ..contract_metadata import CONTRACT_METADATA
from ..contract_registry import decode_function_input
from ..global_context import context
from ..utils import normalize_contract_address
from ..transactions import transact, transfer_funds
from ..compilation.verified_source_code import fetch_verified_contract_source as _fetch_verified_contract_source

from . import cmdline, rename, subcommand_callable


contract_handler = subcommand_callable(cmdline, 'contract', __subcommand_doc='Manage contracts and their metadata')


@contract_handler
def address(address_string: str, **kwargs):
    '''
    Parse an address string into an address. The string can be in checksummed, non-checksummed,
    or hex format.
    '''
    return normalize_contract_address(address_string)

@contract_handler
def deploy(contract_name,
           constructor_args: List[str] = [],
           tx_args: Dict[str, str] = {},
           **kwargs):
    '''
    Deploy a contract and return the deployed contract instance.

    Registers it in the contract registry. Optionally, you can provide the contract source code, or a list of source files to
    compile the contract on the file.
    '''
    contract = CONTRACT_METADATA[contract_name]
    return contract.deploy(*constructor_args, **tx_args)

@contract_handler
def get_default_import_remappings(sources: List[str], **kwargs):
    '''
    Print the default import remappings.
    '''
    _import_remappings = {}

    def add_solidity_includes_remappings(solidity_includes_path):
        for name in os.listdir(solidity_includes_path):
            if os.path.isdir(os.path.join(solidity_includes_path, name, 'contracts')):
                _import_remappings[f'{name}'] = os.path.join(solidity_includes_path, name, 'contracts') + '/'
            else:
                _import_remappings[f'{name}'] = os.path.join(solidity_includes_path, name) + '/'

    # check next to the source files for includes
    for source in sources:
        dirname = os.path.dirname(os.path.abspath(source))
        solidity_includes_path = os.path.join(dirname, 'solidity-includes')
        if not os.path.exists(solidity_includes_path):
            continue

        assert os.path.isdir(solidity_includes_path)
        add_solidity_includes_remappings(solidity_includes_path, )


    # check the current directory for includes
    if os.path.exists('solidity-includes'):
        assert os.path.isdir('solidity-includes')
        add_solidity_includes_remappings('solidity-includes')

    return _import_remappings


@contract_handler
def compile(sources: List[str], import_remappings: Dict[str, str]=None, no_default_remappings=False, **kwargs):
    '''
    Compile a contract. Returns the contract object. Optionally, you can provide the contract
    source code, or a list of source files to compile the contract on the file.

    THIS WILL NOT STORE THIS INFORMATION ACROSS RUNS AND IS ONLY FOR TESTING PURPOSES. IF YOU WANT
    TO STORE THIS INFORMATION, USE `ethpwn contract register` INSTEAD.

    By default, the compiler will look for the default import remappings in the following places:
    - It looks for a `solidity-includes` directory in the current directory
    - It looks for any `solidity-includes` directories which are adjacent to the source files

    If you don't want to use the default import remappings, you can pass the `--no-default-remappings`
    flag.

    :param source: the source code of the contract
    :param source_filename: the filename of the source code of the contract
    :param source_files: a list of source files to compile the contract
    :param import_remappings: a list of import remappings to use when compiling the contract

    :return: the contract object
    '''
    # import ipdb; ipdb.set_trace()

    if no_default_remappings:
        _import_remappings = {}
    else:
        _import_remappings = get_default_import_remappings(sources)

    _import_remappings.update(import_remappings or {})

    if _import_remappings:
        CONTRACT_METADATA.solidity_compiler.add_import_remappings(_import_remappings)

    CONTRACT_METADATA.compile_solidity_files(sources, **kwargs)
    return CONTRACT_METADATA

@contract_handler
def register(contract_name: str, contract_address: HexBytes,
             source_files: List[str]=None,
             no_default_remappings: bool=False,
             import_remappings: Dict[str, str]=None,
             recover_opt_settings: bool=False,
             solc_version: str=None,
             **kwargs
            ):
    '''
    Register an instance of the contract `contract_name` at `contract_address` in the contract registry.
    Optionally, you can provide the contract source code, or a list of source files to compile the
    contract first.

    If `find_optimizer_settings_to_match_bytecode` is set, the compiler will try to find the
    optimizer settings that were used to compile the contract. This is useful if you want to
    register a contract that was already deployed, but you don't know the optimizer settings that
    were used to compile it. This is a slow process, so it is disabled by default.

    :param contract_name: the name of the contract
    :param contract_address: the address of the contract
    :param source_files: a list of source files to compile the contract
    :param no_default_remappings: whether to avoid using the default import remappings
    :param import_remappings: a list of import remappings to use when compiling the contract
    :param recover_opt_settings: whether to try to recover the optimizer settings that were used to compile the contract
    '''

    if no_default_remappings:
        _import_remappings = {}
    else:
        _import_remappings = get_default_import_remappings(source_files)
    _import_remappings.update(import_remappings or {})

    if _import_remappings:
        CONTRACT_METADATA.solidity_compiler.add_import_remappings(_import_remappings)

    best_kwargs = {}
    if recover_opt_settings:
        # from .solidity_utils import try_match_optimizer_settings
        if source_files is not None:
            assert type(source_files) is list
            do_compile = functools.partial(
                CONTRACT_METADATA.solidity_compiler.compile_files,
                source_files
            )
        else:
            raise ValueError(f"Invalid parameters given: {source_files=!r} not given, but requested to recover optimizer settings.")
        bin_runtime = context.w3.eth.get_code(contract_address)
        best_kwargs, meta, final_bytecode = try_match_optimizer_settings(
            do_compile,
            contract_name,
            bin_runtime=bin_runtime,
            solc_versions=ethcx.get_installable_solc_versions() if solc_version is None else [solc_version],
        )

    if source_files is not None:
        CONTRACT_METADATA.compile_solidity_files(source_files, **best_kwargs)

    contract = CONTRACT_METADATA[contract_name]
    return contract.get_contract_at(contract_address)

@contract_handler
def fetch_verified_contract_source(address, api_key: str = None, network: str = None, **kwargs):
    '''
    Fetch the verified source code for the contract at `address` from Etherscan and register it in
    the code-registry. If the contract is not verified, an error is raised. If the contract is
    already registered, it is returned.
    '''
    return _fetch_verified_contract_source(normalize_contract_address(address), api_key=api_key, network=network, **kwargs)


@contract_handler
def decode_calldata(target_contract: HexBytes=None, calldata: HexBytes=None, tx_hash: HexBytes=None, guess: bool=False, **kwargs):
    '''
    Decode a transaction. Either `target_contract`+`calldata` or `tx_hash` must be provided.
    '''
    if tx_hash is not None:
        tx = context.w3.eth.get_transaction(tx_hash)
        if target_contract is None:
            target_contract = tx.to
        if calldata is None:
            calldata = tx.input

    assert target_contract is not None
    assert calldata is not None

    contract, metadata, decoded = decode_function_input(target_contract, calldata, guess=guess)
    if metadata is not None:
        metadata = (metadata.source_file, metadata.contract_name)
    return metadata, decoded


contracts_name_handler = subcommand_callable(contract_handler, 'name', __subcommand_doc='Manage contract names')

@contracts_name_handler
def add(address: HexBytes, name: str, **kwargs):
    '''
    Add a contract name for a contract address.
    '''
    register_contract_name(address, name)

@contracts_name_handler
def get(address: HexBytes, **kwargs):
    '''
    Get the names of a contract address.
    '''
    return names_for_contract(contract_address)

@contracts_name_handler
@rename('list')
def _list(**kwargs):
    '''
    Show all contract names.
    '''
    table = Table()
    table.add_column("Contract Address")
    table.add_column("Contract Name")
    for name, address in contract_names().name_to_address.items():
        table.add_row(
            normalize_contract_address(address),
            name
        )
    return table
