
import json
import os
from typing import Dict, Iterator, Tuple

from hexbytes import HexBytes
from web3.types import TxReceipt
from web3.datastructures import AttributeDict

from rich.tree import Tree
from rich.table import Table

from .utils import normalize_contract_address
from .contract_metadata import CONTRACT_METADATA, ContractMetadata
from .hashes import lookup_signature_hash
from .config import get_contract_registry_dir, get_logged_deployed_contracts_dir
from .config.wallets import Wallet, get_wallet_by_address
from .global_context import context
from .serialization_utils import deserialize_from_file, register_serializable, serialize_to_file, Serializable

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
            contract_addr = normalize_contract_address(tx_receipt['contractAddress'])
            assert contract_address is None or normalize_contract_address(contract_address) == contract_addr
            return contract_addr, HexBytes(tx_hash), tx_receipt
    else:
        assert tx_hash is None or HexBytes(tx_hash) == HexBytes(tx_receipt['transactionHash'])
        assert contract_address is None or HexBytes(contract_address) == HexBytes(tx_receipt['contractAddress'])
        return HexBytes(tx_receipt['contractAddress']), HexBytes(tx_receipt['transactionHash']), tx_receipt


class Contract(Serializable):
    def __init__(self, address=None, metadata=None, deploy_tx_hash=None, deploy_tx_receipt=None, deploy_wallet=None) -> None:
        super().__init__()
        self.address: HexBytes = None
        self.deploy_tx_hash: HexBytes = None
        self.deploy_tx_receipt: TxReceipt = None
        self.metadata: ContractMetadata = metadata

        self.address, self.deploy_tx_hash, self.deploy_tx_receipt = \
            best_effort_get_contract_address_and_tx_hash_and_receipt(address, deploy_tx_hash, deploy_tx_receipt)

        self.deploy_wallet = deploy_wallet if deploy_wallet is not None else get_wallet_by_address(self.address)

    # implement the Serializable interface
    def to_serializable(self):
        return {
            'address': self.address,
            'metadata': self.metadata,
            'deploy_tx_hash': self.deploy_tx_hash,
            'deploy_tx_receipt': self.deploy_tx_receipt,
            'deploy_wallet': self.deploy_wallet,
        }

    @staticmethod
    def from_serializable(data):
        return Contract(**data)

    def __rich_console__(self, console, options):
        s = f'Contract {self.address} ({self.metadata.contract_name})'
        if self.deploy_tx_hash is not None:
            s += f' deployed at {self.deploy_tx_hash}'
        yield s
        # now yield the metadata
        yield from self.metadata.__rich_console__(console, options)


    def w3(self):
        return context.w3.eth.contract(address=self.address, abi=self.metadata.abi)

    def merge(self, other: 'Contract'):
        self.update(other.address, other.metadata, other.deploy_tx_hash, other.deploy_tx_receipt, other.deploy_wallet)

    def update(self, address=None, metadata=None, deploy_tx_hash=None, deploy_tx_receipt=None, deploy_wallet=None) -> bool:
        changed = False
        if address is not None:
            assert self.address is None or self.address == address
            changed = changed or self.address != address
            self.address = address
        if deploy_tx_hash is not None:
            assert self.deploy_tx_hash is None or self.deploy_tx_hash == deploy_tx_hash
            changed = changed or self.deploy_tx_hash != deploy_tx_hash
            self.deploy_tx_hash = deploy_tx_hash
        if deploy_tx_receipt is not None:
            assert self.deploy_tx_receipt is None or self.deploy_tx_receipt == deploy_tx_receipt
            changed = changed or self.deploy_tx_receipt != deploy_tx_receipt
            self.deploy_tx_receipt = deploy_tx_receipt
        if metadata is not None:
            changed = changed or self.metadata != metadata
            self.metadata = metadata
        if deploy_wallet is not None:
            assert self.deploy_wallet is None or self.deploy_wallet == deploy_wallet
            changed = changed or self.deploy_wallet != deploy_wallet
            self.deploy_wallet = deploy_wallet
        return changed

class ContractRegistry:
    def __init__(self) -> None:
        self.registered_contracts: Dict[str, Contract] = {}

    def register_contract_metadata(self,
                                   metadata: 'ContractMetadata',
                                   address=None,
                                   deploy_tx_hash=None,
                                   deploy_tx_receipt: TxReceipt = None,
                                   deploy_wallet=None,
                                   ):
        contract = Contract(
            address=address,
            metadata=metadata,
            deploy_tx_hash=deploy_tx_hash,
            deploy_tx_receipt=deploy_tx_receipt,
            deploy_wallet=deploy_wallet,
            )

        if contract.address in self.registered_contracts:
            self.registered_contracts[contract.address].merge(contract)
        else:
            self.registered_contracts[contract.address] = contract

        # on change, save the registry
        self.store(get_contract_registry_dir())

    # handler for `x in registry`
    def __contains__(self, contract_address) -> bool:
        address = normalize_contract_address(contract_address)
        return address in self.registered_contracts

    # handler for `registry[contract_address]`
    def __getitem__(self, contract_address) -> Contract:
        address = normalize_contract_address(contract_address)
        return self.registered_contracts[address]

    def get(self, contract_address, default=None) -> Contract:
        address = normalize_contract_address(contract_address)
        return self.registered_contracts.get(address, default)

    # handler for `registry[contract_address] = contract`
    def __setitem__(self, contract_address, contract: Contract):
        address = normalize_contract_address(contract_address)
        self.registered_contracts[address] = contract

    def __iter__(self) -> Iterator[Tuple[HexBytes, Contract]]:
        return self.registered_contracts.items().__iter__()

    def store(self, contract_registry_dir):
        os.makedirs(contract_registry_dir, exist_ok=True)
        assert os.path.isdir(contract_registry_dir)

        for address, contract in self.registered_contracts.items():
            serialize_to_file(contract, path=os.path.join(contract_registry_dir, HexBytes(address).hex() + ".json"))

    def load(contract_registry_dir) -> 'ContractRegistry':
        if not os.path.isdir(contract_registry_dir):
            return False

        self = ContractRegistry()

        for contract_file_name in os.listdir(contract_registry_dir):
            contract = deserialize_from_file(path=os.path.join(contract_registry_dir, contract_file_name))
            assert contract.address is not None and contract_file_name == f"{HexBytes(contract.address).hex()}.json"
            self.registered_contracts[contract.address] = contract

        return self

    def __rich_console__(self, console, options):
        table = Table(title="Contract Registry")
        table.add_column("Address")
        table.add_column("Name")
        table.add_column("Deployed")
        table.add_column("Deployer")
        table.add_column("Source file")
        for address, contract in self.registered_contracts.items():
            table.add_row(
                contract.address,
                contract.metadata.contract_name,
                contract.deploy_tx_hash if contract.deploy_tx_hash is not None else "N/A",
                str(contract.deploy_wallet) if contract.deploy_wallet is not None else "N/A",
                contract.metadata.source_file,
            )
        yield table



CONTRACT_REGISTRY: ContractRegistry = None
def contract_registry() -> ContractRegistry:
    global CONTRACT_REGISTRY
    if CONTRACT_REGISTRY is None:
        CONTRACT_REGISTRY = load_or_create_contract_registry()
    return CONTRACT_REGISTRY

def load_or_create_contract_registry() -> ContractRegistry:
    contract_registry_dir = get_contract_registry_dir()
    if os.path.isdir(contract_registry_dir):
        return ContractRegistry.load(contract_registry_dir)
    else:
        return ContractRegistry()

def register_deployed_contract(metadata, address=None, deploy_tx_hash=None, deploy_tx_receipt: TxReceipt = None):
    reg = contract_registry()
    reg.register_contract_metadata(
        metadata,
        address,
        deploy_tx_hash,
        deploy_tx_receipt,
        deploy_wallet=get_wallet_by_address(deploy_tx_receipt['from'])
    )

def register_contract_at_address(metadata, address):
    reg = contract_registry()
    reg.register_contract_metadata(
        metadata,
        address,
        deploy_wallet=get_wallet_by_address(address)
    )

def decode_function_input(contract_address, input, guess=False):
    from .contract_metadata import CONTRACT_METADATA
    contract_address = normalize_contract_address(contract_address)

    registry = contract_registry()
    if contract_address in registry:
        contract = registry[contract_address]
        metadata = contract.metadata
        return contract, metadata, *metadata.decode_function_input(input)
    elif guess:
        for contract_name, metadata in CONTRACT_METADATA.contracts[''].items():
            try:
                return None, metadata, *metadata.decode_function_input(input)
            except ValueError as e:
                continue

        # worst case: We don't know what this contract is, so we just at least try to decode the function selector
        selector = input.hex()[2:10]
        if len(selector) == 8:
            func_signature = lookup_signature_hash(selector)
            if func_signature is not None:
                return None, None, (func_signature, [input[4:]])

    return None