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
from ..contract_labels import contract_labels, label_for_contract, register_contract_label, labels_for_contract, contract_by_label
from ..contract_metadata import CONTRACT_METADATA
from ..contract_registry import convert_contract_registry_to_encoding, decode_function_input
from ..global_context import context
from ..utils import normalize_contract_address
from ..transactions import transact, transfer_funds
from ..compilation.verified_source_code import fetch_verified_contract as _fetch_verified_contract

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
    cur_dir_solidity_includes_path = os.path.abspath(os.path.join(os.getcwd(), 'solidity-includes'))
    if os.path.exists(cur_dir_solidity_includes_path):
        assert os.path.isdir(cur_dir_solidity_includes_path)
        add_solidity_includes_remappings(cur_dir_solidity_includes_path)

    return _import_remappings


@contract_handler
def compile(sources: List[str], import_remappings: Dict[str, str]=None, no_default_remappings=False, **kwargs):
    '''
    Compile a contract. Returns the contract object. Optionally, you can provide the contract
    source code, or a list of source files to compile the contract on the file.

    THIS WILL NOT STORE THIS INFORMATION ACROSS RUNS AND IS ONLY FOR TESTING PURPOSES. IF YOU WANT
    TO STORE THIS INFORMATION, USE `ethpwn contract register` INSTEAD.

    By default, the compiler will look for the default import remappings in the following places:
    1) It looks for a `solidity-includes` directory in the current directory.
    2) It looks for any `solidity-includes` directories which are adjacent to the source files.

    If you don't want to use the default import remappings, you can pass the `--no-default-remappings`
    flag.

    :param sources: a list of source files to compile the contract
    :param import_remappings: a list of import remappings to use when compiling the contract
    :param no_default_remappings: whether to avoid using the default import remappings
    :param kwargs: additional arguments to pass to the compiler

    :return: the contract object
    '''

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
def convert_registry(from_encoding: str, to_encoding: str, **kwargs):
    '''
    Convert the contract registry from one encoding to another. Valid encodings: 'json', 'msgpack'

    :param from_encoding: the encoding to convert from
    :param to_encoding: the encoding to convert to

    '''
    if from_encoding is None:
        from_encoding = 'json'
    if to_encoding is None:
        to_encoding = 'msgpack'

    assert to_encoding in ['json', 'msgpack']
    assert from_encoding in ['json', 'msgpack']
    assert from_encoding != to_encoding

    convert_contract_registry_to_encoding(from_encoding, to_encoding)

def recover_optimizer_settings(bin_runtime, contract_name, sources, solc_version=None):
    assert type(sources) is list
    do_compile = functools.partial(
        CONTRACT_METADATA.solidity_compiler.compile_files,
        sources
    )
    best_kwargs, meta, final_bytecode = try_match_optimizer_settings(
            do_compile,
            contract_name,
            bin_runtime=bin_runtime,
            solc_versions=ethcx.get_installable_solc_versions() if solc_version is None else [solc_version],
        )
    return best_kwargs, meta, final_bytecode

def update_import_remappings(sources, no_default_remappings=False, import_remappings=None, **kwargs):
    if no_default_remappings:
        _import_remappings = {}
    else:
        _import_remappings = get_default_import_remappings(sources)
    _import_remappings.update(import_remappings or {})

    if _import_remappings:
        CONTRACT_METADATA.solidity_compiler.add_import_remappings(_import_remappings)

@contract_handler
def deploy( contract_name: str,
            sources: List[str],
            constructor_args: List[str]=[],
            no_default_remappings: bool=False,
            import_remappings: Dict[str, str]=None,
            recover_opt_settings: bool=False,
            solc_version: str=None,
            tx_args: Dict[str, str] = {},
           **kwargs):
    '''
    Deploy a contract and return the deployed contract instance.

    Registers it in the contract registry. Optionally, you can provide the contract source code, or a list of source files to
    compile the contract on the file.
    '''
    if not sources:
        raise ValueError("Must provide sources to deploy a contract")

    update_import_remappings(
        sources,
        no_default_remappings=no_default_remappings,
        import_remappings=import_remappings
    )
    if recover_opt_settings:
        best_kwargs, _, _ = recover_opt_settings(
            None,
            contract_name,
            sources,
            solc_version=solc_version
        )
    else:
        best_kwargs = {}

    CONTRACT_METADATA.compile_solidity_files(sources, **best_kwargs)

    contract = CONTRACT_METADATA[contract_name]
    return contract.deploy(*constructor_args, **tx_args)

import ipdb; ipdb.set_trace()
@contract_handler
def register(
    contract_address: HexBytes,
    contract_name: str,
    sources: List[str],
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

    :param contract_address: the address of the contract on the blockchain
    :param contract_name: the name of the contract class
    :param sources: source files to compile
    :param no_default_remappings: whether to avoid using the default import remappings
    :param import_remappings: a list of import remappings to use when compiling the contract
    :param recover_opt_settings: whether to try to recover the optimizer settings that were used to compile the contract
    '''
    if not sources:
        raise ValueError("Must provide sources to register a contract")

    update_import_remappings(
        sources,
        no_default_remappings=no_default_remappings,
        import_remappings=import_remappings
    )
    if recover_opt_settings:
        bin_runtime = context.w3.eth.get_code(contract_address)
        best_kwargs, _, _ = recover_opt_settings(
            bin_runtime,
            contract_name,
            sources,
            solc_version=solc_version
        )
    else:
        best_kwargs = {}

    CONTRACT_METADATA.compile_solidity_files(sources, **best_kwargs)

    contract = CONTRACT_METADATA[contract_name]
    return contract.get_contract_at(contract_address)

@contract_handler
def fetch_verified_contract(address, api_key: str = None, network: str = None, **kwargs):
    '''
    Fetch the verified source code for the contract at `address` from Etherscan and register it in
    the code-registry. If the contract is not verified, an error is raised. If the contract is
    already registered, it is returned.
    '''
    return _fetch_verified_contract(normalize_contract_address(address), api_key=api_key, network=network, **kwargs)


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
