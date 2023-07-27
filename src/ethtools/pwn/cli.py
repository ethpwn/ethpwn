'''
Helpful functions available in the CLI.
'''

import functools

from .compilation.compiler_solidity import try_match_optimizer_settings
from .contract_metadata import CONTRACT_METADATA
from .global_context import context
from .utils import normalize_contract_address
from .transactions import transact, transfer_funds
from .compilation.verified_source_code import fetch_verified_contract_source

def add_default_node_url(node_url):
    '''
    Adds a default node URL to the context. If the node is not available, a warning is printed.
    All default node URLs are tried in order until one is available.
    '''
    if context.connect_http(node_url, can_fail=True):
        context.logger.warning(
            'Default node set to %s, however we were unable to connect to it.',
            node_url
            )
    raise NotImplementedError('TODO: Implement this function')

def address(address_string):
    '''
    Parse an address string into an address. The string can be in checksummed, non-checksummed,
    or hex format.
    '''
    return normalize_contract_address(address_string)

def deploy(contract_name,
           *constructor_args,
           source=None, source_filename=None, source_files=None, import_remappings=None,
           **kwargs):
    '''
    Deploy a contract. Returns the address of the deployed contract. Registers it in the contract
    registry. Optionally, you can provide the contract source code, or a list of source files to
    compile the contract on the file.
    '''
    if import_remappings:
        CONTRACT_METADATA.solidity_compiler.add_import_remappings(import_remappings)

    if source is not None:
        CONTRACT_METADATA.add_solidity_source(source, source_filename)

    if source_files is not None:
        CONTRACT_METADATA.add_contracts_from_solidity_files(source_files)

    contract = CONTRACT_METADATA[contract_name]
    return contract.deploy(*constructor_args, **kwargs)


def contract_at(contract_name, _address,
                source=None, source_filename=None, source_files=None, import_remappings=None,
                find_optimizer_settings_to_match_bytecode=False,
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
        bin_runtime = context.w3.eth.get_code(_address)
        best_kwargs, meta, final_bytecode = try_match_optimizer_settings(do_compile, contract_name, bin_runtime=bin_runtime)

    if source is not None:
        CONTRACT_METADATA.add_solidity_source(source, source_filename)

    if source_files is not None:
        CONTRACT_METADATA.add_contracts_from_solidity_files(source_files, **best_kwargs)

    contract = CONTRACT_METADATA[contract_name]
    return contract.get_contract_at(_address)

def verified_contract_at(address, api_key=None):
    '''
    Fetch the verified source code for the contract at `address` from Etherscan and register it in
    the code-registry. If the contract is not verified, an error is raised. If the contract is
    already registered, it is returned.
    '''
    fetch_verified_contract_source(address, api_key=api_key)