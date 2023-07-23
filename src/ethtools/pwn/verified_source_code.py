import json
import os
import time
from typing import Any, Dict, Tuple
from hexbytes import HexBytes
import requests
from .config.credentials import get_etherscan_api_key
from .contract_metadata import CONTRACT_METADATA
from .contract_registry import contract_registry

class EtherscanAPIError(Exception):
    pass

class NotVerifiedError(Exception):
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
def _pull_verified_source_from_etherscan(contract_address, api_key):
    url = f"https://api.etherscan.io/api?module=contract&action=getsourcecode&address={contract_address}&apikey={api_key}"
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
        assert result['Proxy'] == "0"
        assert not result['Implementation']
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
def pull_verified_source_from_etherscan(contract_address, api_key=None):
    api_key = get_etherscan_api_key(api_key)
    if api_key is None:
        raise ValueError("You need to set an etherscan api key in your config.json file to use the verified source codes feature.")
    
    cache_key = (contract_address, api_key)
    if cache_key in CACHED_REQUESTS and time.time() < CACHED_REQUESTS[cache_key][0] + 60 * 5: # 5 minute cache hold
        return CACHED_REQUESTS[cache_key][1]
    try:
        result = _pull_verified_source_from_etherscan(contract_address, api_key=api_key)
        CACHED_REQUESTS[cache_key] = (time.time(), result)
        return result
    except NotVerifiedError:
        return None

def _parse_verified_source_code_into_registry(contract_address, result, origin='etherscan'):
    source = result['SourceCode']
    source = source.strip().replace('\r\n', '\n')
    assert origin == 'etherscan'
    
    compiler_kwargs = {}

    compiler_kwargs['optimizer_settings'] = {
        'enabled': result['OptimizationUsed'],
        'runs': result['Runs']
    }

    if result['CompilerVersion']:
        solidity_version = result['CompilerVersion'].split('+commit')[0]
        assert solidity_version.startswith('v')
        solidity_version = solidity_version[1:]
        compiler_kwargs['solc_version'] = solidity_version
    
    if source.strip()[:2] == '{{' and source.strip()[-2:] == '}}':
        output_json = json.loads(source.strip()[1:-1])
        if output_json['language'] != 'Solidity':
            raise ValueError(f"Verified source code from {origin} is not in Solidity, unsupported.")

        opt_settings = output_json.get('settings', {}).get('optimizer', None)
        if opt_settings is not None:
            assert result['OptimizationUsed'] == opt_settings['enabled']
            assert result['Runs'] == opt_settings['runs']

        CONTRACT_METADATA.add_solidity_sources_dict(output_json['sources'], **compiler_kwargs)
    else:
        # we assume that it is just the text of the source code
        CONTRACT_METADATA.add_solidity_source(source, f'verified/{contract_address}.sol', **compiler_kwargs)


def add_verified_source_to_contract_registry(contract_address, api_key=None):
    if contract_address in contract_registry():
        raise ValueError(f"Contract address {contract_address} is already in the contract registry.")
    
    try:
        result = pull_verified_source_from_etherscan(contract_address, api_key=api_key)
        if result is None:
            return None
        assert result['ContractName']
        _parse_verified_source_code_into_registry(contract_address, result, origin='etherscan')
        return CONTRACT_METADATA[result['ContractName']].get_contract_at(contract_address)
    except NotVerifiedError:
        return None
    