# coding: utf-8
import functools
import logging
from ethpwn.prelude import *
from ethpwn.solidity_utils import *
from rich import inspect, print

context.connect_http('https://eth-sepolia.g.alchemy.com/v2/CIlvNRJd1iqhTV5d_KIBxWX_qCq0j71v')
context.log_level = "DEBUG"
logging.basicConfig(level=logging.WARNING)

print(contract_registry())
compiler = CONTRACT_METADATA.compiler
os.chdir('pwn/examples/ethernaut-ethpwn-solutions/')
compiler.add_import_remappings({'openzeppelin-contracts-08': './__solidity_includes/openzeppelin-contracts-0.8/contracts/'})


contract = contract_registry()['0xe1c5Ea83e0F40e2139589E4Df49Ce367c569bc59']
bin_runtime = context.w3.eth.get_code(contract.address)
solc_binary_cache = {}

def do_compile(**kwargs):
    global solc_binary_cache
    solc_binary_version = kwargs.get('solc_version')
    if kwargs.get('solc_binary', None) is None:
        if solc_binary_version in solc_binary_cache:
            solc_binary = solc_binary_cache[solc_binary_version]
        else:
            solcx.install_solc(solc_binary_version)
            solc_binary = solcx.install.get_executable(solc_binary_version)
            solc_binary_cache[solc_binary_version] = solc_binary
        kwargs['solc_binary'] = solc_binary

    return compiler.compile_files(['./doubleentrypoint/contract.sol'], **kwargs)

x = try_out_optimizer_settings(do_compile, 'Forta', bin_runtime=bin_runtime, solc_versions=[v for v in solcx.get_installed_solc_versions() if v.minor==8])

rich.print(x)