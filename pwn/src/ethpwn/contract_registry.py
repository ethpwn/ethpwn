
import json
import os
from typing import Dict

from hexbytes import HexBytes
from web3.types import TxReceipt
from web3.datastructures import AttributeDict

from .hashes import lookup_signature_hash
from .config import get_logged_deployed_contracts_dir
from .config.wallets import Wallet, get_wallet_by_address
from .contract_metadata import CONTRACT_METADATA, ContractMetadata
from .global_context import context
from .json_utils import json_load, json_dump

def best_effort_get_contract_address_and_tx_hash_and_receipt(contract_address=None, tx_hash=None, tx_receipt: TxReceipt=None):
    assert contract_address is not None or tx_hash is not None or tx_receipt is not None
    if tx_receipt is None:
        if tx_hash is None:
            # get the transaction that deployed the contract
            assert contract_address is not None

            # TODO: find a way (maybe by Etherscan API) to get the transaction hash of the deployment transaction
            return contract_address, None, None
        else:
            tx_receipt = context.w3.eth.getTransactionReceipt(tx_hash)
            assert contract_address is None or HexBytes(contract_address) == HexBytes(tx_receipt['contractAddress'])
            return HexBytes(tx_receipt['contractAddress']), HexBytes(tx_hash), tx_receipt
    else:
        assert tx_hash is None or HexBytes(tx_hash) == HexBytes(tx_receipt['transactionHash'])
        assert contract_address is None or HexBytes(contract_address) == HexBytes(tx_receipt['contractAddress'])
        return HexBytes(tx_receipt['contractAddress']), HexBytes(tx_receipt['transactionHash']), tx_receipt

class Contract:
    def __init__(self, contract_address=None, metadata=None, deploy_tx_hash=None, deploy_tx_receipt=None, auto_deployed_by_ethpwn=False) -> None:
        self.address: HexBytes = None
        self.deploy_tx_hash: HexBytes = None
        self.deploy_tx_receipt: TxReceipt = None
        self.metadata: ContractMetadata = metadata
        self.auto_deployed_by_ethpwn = auto_deployed_by_ethpwn

        self.address, self.deploy_tx_hash, self.deploy_tx_receipt = \
            best_effort_get_contract_address_and_tx_hash_and_receipt(
                contract_address, deploy_tx_hash, deploy_tx_receipt
                )

    def load(path) -> 'Contract':
        data = json_load(path)
        return Contract(
            contract_address=HexBytes(data['address']),
            metadata=data['metadata'],
            deploy_tx_hash=HexBytes(data['deploy_tx_hash']),
            deploy_tx_receipt=data['deploy_tx_receipt'],
            )

    def save(self, path):
        data = {
            'address': self.address.hex(),
            'deploy_tx_hash': self.deploy_tx_hash.hex(),
            'deploy_tx_receipt': self.deploy_tx_receipt,
            'metadata': self.metadata.name,
            'deploy_wallet': self.deploy_wallet,
        }
        json_dump(data, path)

    def merge(self, other: 'Contract'):
        self.update(other.address, other.metadata, other.deploy_tx_hash, other.deploy_tx_receipt, other.deploy_wallet)

    def update(self, address=None, metadata=None, deploy_tx_hash=None, deploy_tx_receipt=None, deploy_wallet=None):
        if address is not None:
            assert self.address is None or self.address == address
            self.address = address
        if deploy_tx_hash is not None:
            assert self.deploy_tx_hash is None or self.deploy_tx_hash == deploy_tx_hash
            self.deploy_tx_hash = deploy_tx_hash
        if deploy_tx_receipt is not None:
            assert self.deploy_tx_receipt is None or self.deploy_tx_receipt == deploy_tx_receipt
            self.deploy_tx_receipt = deploy_tx_receipt
        if metadata is not None:
            assert self.metadata is None or self.metadata == metadata
            self.metadata = metadata
        if deploy_wallet is not None:
            assert self.deploy_wallet is None or self.deploy_wallet == deploy_wallet
            self.deploy_wallet = deploy_wallet

class ContractRegistry:
    def __init__(self) -> None:
        self.registered_contracts = {}

    def register_contract_metadata(self,
                                   metadata: ContractMetadata,
                                   address=None,
                                   deploy_tx_hash=None,
                                   deploy_tx_receipt: TxReceipt = None,
                                   deploy_wallet=None,
                                   ):
        contract = Contract(
            contract_address=address,
            metadata=metadata,
            deploy_tx_hash=deploy_tx_hash,
            deploy_tx_receipt=deploy_tx_receipt,
            deploy_wallet=deploy_wallet,
            )

        if contract.address in self.registered_contracts:
            self.registered_contracts[contract.address].merge(contract)

        self.registered_contracts[contract.address] = contract

    def load(self, contract_registry_path):
        assert os.path.isdir(contract_registry_path)
        for contract_path in os.listdir(contract_registry_path):
            contract = Contract()
            contract.load(contract_path)
            self.registered_contracts[contract.address] = contract

CONTRACT_REGISTRY = None
def get_contract_registry():
    global CONTRACT_REGISTRY
    if CONTRACT_REGISTRY is None:
        CONTRACT_REGISTRY = load_or_create_contract_registry()
    return CONTRACT_REGISTRY

def load_or_create_contract_registry():
    contract_registry_path = get_contract_registry_path()


def log_deployed_contract(metadata, address=None, deploy_tx_hash=None, deploy_tx_receipt: TxReceipt = None):

    deployed_contracts_path = get_logged_deployed_contracts_dir()
    os.makedirs(deployed_contracts_path, exist_ok=True)
    deployed_contracts_path += f"{address}.json"

    with open(deployed_contracts_path, 'w') as f:
        json_dump({
            'deploy_wallet': get_wallet_by_address(deploy_tx_receipt['from']).to_serializable_dict(),
            'tx_hash': deploy_tx_receipt,
            'tx_receipt': deploy_tx_receipt,
            'metadata': metadata.to_json_dict(),
        }, f)

def all_previously_deployed_contracts():
    deployed_contracts_path = get_logged_deployed_contracts_dir()
    for file in os.listdir(deployed_contracts_path):
        if file.endswith('.json'):
            with open(deployed_contracts_path + file, 'r') as f:
                data = json.load(f)
                wallet = Wallet.from_json_dict(data['from_wallet'])
                tx_hash = HexBytes.fromhex(data['tx_hash'])
                tx_receipt = TxReceipt(data['tx_receipt'])
                metadata = ContractMetadata.from_json_dict(data['metadata'])
                yield wallet, tx_hash, tx_receipt, metadata

def all_previously_deployed_contracts_with_balance_remaining():
    for wallet, tx_hash, tx_receipt, metadata in all_previously_deployed_contracts():
        balance = context.w3.eth.get_balance(tx_receipt.contractAddress)
        if balance > 0:
            yield wallet, tx_hash, tx_receipt, metadata, balance

TYPED_CONTRACTS: Dict[str, 'ContractMetadata'] = {}

def register_typed_contract(address: str, contract_metadata: 'ContractMetadata'):
    TYPED_CONTRACTS[address] = contract_metadata

def get_typed_contract(address: str):
    return TYPED_CONTRACTS.get(address, None)

def decode_function_input(address, input, guess=False):
    if address in TYPED_CONTRACTS:
        metadata = TYPED_CONTRACTS[address]
        return metadata, *metadata.decode_function_input(input)
    elif guess:
        for name, metadata in CONTRACT_METADATA.contract_info[''].items():
            try:
                return metadata, *metadata.decode_function_input(input)
            except ValueError as e:
                continue

    # worst case: We don't know what this contract is, so we just at least try to decode the function selector
    selector = input.hex()[2:10]
    if len(selector) == 8:
        func_signature = lookup_signature_hash(selector)
        if func_signature is not None:
            return None, func_signature, [input[4:]]

    return None