'''
Helpful functions available in the CLI.
'''

import argparse
import functools
from typing import Dict, List
from hexbytes import HexBytes
import ipdb
from rich import print as rprint

from ..compilation.compiler_solidity import try_match_optimizer_settings
from ..contract_metadata import CONTRACT_METADATA
from ..contract_registry import decode_function_input
from ..global_context import context
from ..utils import normalize_contract_address
from ..transactions import transact, transfer_funds
from ..compilation.verified_source_code import fetch_verified_contract_source

from . import cmdline





@cmdline
def address(address_string: str):
    '''
    Parse an address string into an address. The string can be in checksummed, non-checksummed,
    or hex format.
    '''
    return normalize_contract_address(address_string)

@cmdline
def deploy(contract_name,
           constructor_args: List[str] = [],
           source: str=None, source_filename=None, source_files=None, import_remappings=None,
           tx_args: Dict[str, str] = {}):
    '''
    Deploy a contract. Returns the address of the deployed contract. Registers it in the contract
    registry. Optionally, you can provide the contract source code, or a list of source files to
    compile the contract on the file.
    '''
    if import_remappings:
        CONTRACT_METADATA.solidity_compiler.add_import_remappings(import_remappings)

    if source is not None:
        CONTRACT_METADATA.compile_solidity_string(source, source_filename)

    if source_files is not None:
        CONTRACT_METADATA.compile_solidity_files(source_files)

    contract = CONTRACT_METADATA[contract_name]
    return contract.deploy(*constructor_args, **tx_args)


@cmdline
def contract_at(contract_name: str, contract_address: HexBytes,
                source: str=None, source_filename: str=None, source_files: List[str]=None, import_remappings=None,
                find_optimizer_settings_to_match_bytecode: bool=False,
                ):
    '''
    Get a contract instance at the given address. Registers it in the contract registry.
    '''
    if import_remappings:
        CONTRACT_METADATA.solidity_compiler.add_import_remappings(import_remappings)
    assert source_files is None or (source is None and source_filename is None)

    best_kwargs = {}
    if find_optimizer_settings_to_match_bytecode:
        # from .solidity_utils import try_match_optimizer_settings
        if source is None and source_filename is None:
            do_compile = functools.partial(
                CONTRACT_METADATA.solidity_compiler.compile_source,
                source,
                source_filename
            )
        elif source_files is not None:
            assert type(source_files) is list
            do_compile = functools.partial(
                CONTRACT_METADATA.solidity_compiler.compile_files,
                source_files
            )
        else:
            raise ValueError(f"Invalid parameters given: {source_files=!r} {source=!r} {source_filename=!r}")
        bin_runtime = context.w3.eth.get_code(contract_address)
        best_kwargs, meta, final_bytecode = try_match_optimizer_settings(do_compile, contract_name, bin_runtime=bin_runtime)

    if source is not None:
        CONTRACT_METADATA.compile_solidity_string(source, source_filename)

    if source_files is not None:
        CONTRACT_METADATA.compile_solidity_files(source_files, **best_kwargs)

    contract = CONTRACT_METADATA[contract_name]
    return contract.get_contract_at(contract_address)

@cmdline
def fetch_verified_contract_at(address, api_key=None):
    '''
    Fetch the verified source code for the contract at `address` from Etherscan and register it in
    the code-registry. If the contract is not verified, an error is raised. If the contract is
    already registered, it is returned.
    '''
    return fetch_verified_contract_source(normalize_contract_address(address), api_key=api_key)

@cmdline
def decode_calldata(target_contract: HexBytes=None, calldata: HexBytes=None, tx_hash: HexBytes=None, guess: bool=False):
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
