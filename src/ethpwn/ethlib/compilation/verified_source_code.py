'''
This module handles the on-demand fetching, downloading, compiling and registration of source code into the contract
registry for any verified contract in Etherscan's verified-source-code database.
'''
from copy import deepcopy
import json
import os
import re
import time
from typing import Any, Dict, Tuple
from hexbytes import HexBytes
import requests

from ..utils import normalize_contract_address
from ..config import get_contract_registry_dir
from ..config.credentials import get_etherscan_api_key
from ..contract_metadata import CONTRACT_METADATA
from ..contract_registry import ContractInstance, contract_registry

class EtherscanAPIError(Exception):
    pass

class NotVerifiedError(Exception):
    pass

class AlreadyVerifiedError(Exception):
    pass

class VerifiedSourceCode:
    def __init__(self):
        self.source_code = None

        self.compiler_version = None
        self.optimization_used = None
        self.runs = None
        self.constructor_arguments = None
        self.library = None
        self.license_type = None
        self.proxy = None
        self.implementation = None
        self.swarm_source = None
        self.contract_name = None
        self.evm_version = None

def _pull_verified_source_from_etherscan(contract_address, network, api_key):
    assert api_key is not None

    URL_BASE = 'https://api.etherscan.io'
    if network is not None and network != 'mainnet':
        URL_BASE = f'https://api-{network}.etherscan.io'

    url = URL_BASE + f"/api?module=contract&action=getsourcecode&address={contract_address}&apikey={api_key}"
    response = requests.get(url)
    response.raise_for_status()
    assert response.status_code == 200, "Etherscan API returned non-200 status code in a successful request?"
    response_json = response.json()
    if response_json['status'] != '1':
        raise EtherscanAPIError(f"Etherscan API returned status code {response_json['status']} with message {response_json['message']}: {response_json}")
    result = response_json['result']
    assert len(result) == 1, "Etherscan API returned more than one result for a single contract address?"
    result = result[0]

    if not result['SourceCode']:
        assert result['ABI'] == 'Contract source code not verified'
        assert not result['CompilerVersion']
        assert not result['OptimizationUsed']
        assert not result['Runs']
        assert not result['ConstructorArguments']
        assert not result['Library']
        assert result['LicenseType'] == 'Unknown'
        assert not result['SwarmSource']
        assert not result['ContractName']
        assert result['EVMVersion'] == 'Default'
        raise NotVerifiedError(f"Etherscan API returned no source code for contract address {contract_address}")

    assert result['ABI'] != 'Contract source code not verified'
    assert result['CompilerVersion']
    assert result['OptimizationUsed'] != ''
    assert result['Runs'] != ''
    # assert result['ConstructorArguments'] != ''
    # assert result['Library'] != ''
    # assert result['LicenseType'] != ''
    assert result['Proxy']
    # assert result['Implementation']
    # assert result['SwarmSource']
    assert result['ContractName']
    assert result['EVMVersion'] != ''

    result['Runs'] = int(result['Runs'] or 0)
    result['Proxy'] = int(result['Proxy'])
    result['OptimizationUsed'] = int(result['OptimizationUsed']) != 0
    result['ConstructorArguments'] = HexBytes(result['ConstructorArguments'])
    result["ABI"] = json.loads(result["ABI"])
    result["SourceCode"] = result["SourceCode"]

    assert result
    return result

CACHED_REQUESTS: Dict[Tuple[str, str], Tuple[int, Any]] = {}
def pull_verified_source_from_etherscan(contract_address, network=None, api_key=None):
    api_key = get_etherscan_api_key(api_key)
    if api_key is None:
        raise ValueError("You need to set an etherscan api key in your config.json file to use the verified source codes feature.")

    cache_key = (contract_address, api_key)
    if cache_key in CACHED_REQUESTS and time.time() < CACHED_REQUESTS[cache_key][0] + 60 * 5: # 5 minute cache hold
        return CACHED_REQUESTS[cache_key][1]
    try:
        result = _pull_verified_source_from_etherscan(contract_address, network=network, api_key=api_key)
        CACHED_REQUESTS[cache_key] = (time.time(), result)
        return result
    except NotVerifiedError:
        return None

def _parse_verified_source_code_into_registry(contract_address, result, origin='etherscan'):

    # TODO: should verify that the bytecode at the end matches
    source = result['SourceCode']
    source = source.strip().replace('\r\n', '\n')
    assert origin == 'etherscan'

    compiler_kwargs = {}

    compiler_kwargs['optimizer_settings'] = {
        'enabled': result['OptimizationUsed'],
        'runs': result['Runs']
    }

    assert result['CompilerVersion']

    if result['CompilerVersion'].startswith('vyper:'):
        # vyper
        compiler = 'vyper'
        extension = 'vy'

        vyper_version = result['CompilerVersion'][len('vyper:'):]
        compiler_kwargs['vyper_version'] = vyper_version
    else:
        # solidity
        assert ':' not in result['CompilerVersion']
        compiler = 'solc'
        extension = 'sol'

        solidity_version = result['CompilerVersion'].split('+commit')[0]
        assert re.match('v[0-9]+\.[0-9]+\.[0-9]+', solidity_version)
        solidity_version = solidity_version[1:]
        compiler_kwargs['solc_version'] = solidity_version

    libraries = None
    if result['Library']:
        libraries = {}
        for lib in result['Library'].split(';'):
            lib_name, lib_address = lib.split(':')
            libraries[lib_name] = normalize_contract_address(lib_address)


    if source[:2] == '{"':
        # solidity multi-file version, this is basically the sources dict
        sources_dict = json.loads(source)
        CONTRACT_METADATA.compile_sources_dict(sources_dict, compiler=compiler, libraries=libraries, **compiler_kwargs)
    elif source.strip()[:2] == '{{' and source.strip()[-2:] == '}}':
        # solidity input-json format
        input_json = json.loads(source.strip()[1:-1])
        if input_json['language'] != 'Solidity':
            raise ValueError(f"Verified source code from {origin} is not in Solidity, unsupported.")

        opt_settings = input_json.get('settings', {}).get('optimizer', None)
        if opt_settings is not None:
            # 'enabled' is not always present, see e.g. https://etherscan.io/address/0xC4B599043a5479398eb8Af387b1E36D9A924F8C2#code
            assert result['OptimizationUsed'] == opt_settings.get('enabled', False)
            assert result['Runs'] == opt_settings['runs']
        assert libraries is None or input_json.get('settings', {}).get('libraries', None) == libraries
        compiler_kwargs.pop('optimizer_settings', None)
        CONTRACT_METADATA.compile_standard_json(input_json, compiler=compiler, **compiler_kwargs)
    else:
        # solidity single-file version
        contract_name = result['ContractName']
        CONTRACT_METADATA.compile_string(source, f'<<<verified>>>/{contract_address}/{contract_name}.{extension}', compiler=compiler, libraries=libraries, **compiler_kwargs)


def fetch_verified_contract(contract_address, network=None, api_key=None) -> 'ContractInstance':
    # fastpath: just check if the file exists instead of loading the entire registry

    contract_address = normalize_contract_address(contract_address)
    if not contract_address:
        return None

    if os.path.exists(get_contract_registry_dir() / f'{contract_address.lower()}.json'):
        return
    if contract_registry().get(contract_address):
        return

    if api_key is None:
        api_key = get_etherscan_api_key()

    if api_key is not None:
        try:
            result = pull_verified_source_from_etherscan(contract_address, network=network, api_key=api_key)
            if result is None:
                return None
            assert result['ContractName']
            _parse_verified_source_code_into_registry(contract_address, result, origin='etherscan')
            return CONTRACT_METADATA[result['ContractName']].get_contract_at(contract_address)
        except NotVerifiedError:
            return None
