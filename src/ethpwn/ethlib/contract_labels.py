
import json
import os
from typing import Dict, Iterator, List, Tuple

from hexbytes import HexBytes

from rich.table import Table

from .utils import normalize_contract_address
from .config import get_contract_labels_path

class ContractLabels:
    '''
    Maps contract addresses to contract labels.
    Serialized to the local configuration directory to ensure persistence across runs. This allows us to remember
    all contracts we've referred to by a label in the past.
    '''
    def __init__(self) -> None:
        # each contract can have multiple labels, but each label can only refer to one contract
        self.address_to_labels: Dict[str, List[str]] = {}
        self.label_to_address: Dict[str, str] = {}

    def register_contract_label(self, contract_address, contract_label):
        '''
        Assign the given contract address to a label.
        '''
        contract_address = normalize_contract_address(contract_address)

        assert contract_label not in self.label_to_address

        if contract_address in self.address_to_labels:
            self.address_to_labels[contract_address].append(contract_label)
        else:
            self.address_to_labels[contract_address] = [contract_label]

        self.label_to_address[contract_label] = contract_address
        self.store(get_contract_labels_path())

    def get_contract_labels(self, contract_address) -> List[str]:
        '''
        Get the labels registered for a given contract address.
        '''
        contract_address = normalize_contract_address(contract_address)
        return self.address_to_labels.get(contract_address, [])

    def get_contract_address(self, label) -> str:
        '''
        Get the address of the given contract label.
        '''
        return self.label_to_address.get(label, None)

    def __iter__(self) -> Iterator[Tuple[str, str]]:
        return self.label_to_address.items().__iter__()

    def store(self, contract_labels_path):
        '''
        Store the labels to the given JSON file.
        '''

        with open(contract_labels_path, "w") as f:
            json.dump({HexBytes(addr).hex(): labels for addr, labels in self.address_to_labels.items()}, f, indent=2)

    @staticmethod
    def load(contract_labels_path) -> 'ContractLabels':
        '''
        Load the labels from the given JSON path.
        '''
        if not os.path.isfile(contract_labels_path):
            return False

        self = ContractLabels()
        with open(contract_labels_path, "r") as f:
            self.address_to_labels = {normalize_contract_address(addr): labels for addr, labels in json.load(f).items()}
            self.label_to_address = {label: HexBytes(addr) for addr, labels in self.address_to_labels.items() for label in labels}
        return self

    def __rich_console__(self, console, options):
        table = Table(title="Contract Labels")
        table.add_column("Address")
        table.add_column("Label")
        for address, label in self.address_to_labels.items():
            table.add_row(
                address,
                label
            )
        yield table



CONTRACT_LABELS: ContractLabels = None
def contract_labels() -> ContractLabels:
    '''
    Get the global contract labels. Loads the registry from disk if it is not already loaded.
    '''
    global CONTRACT_LABELS
    if CONTRACT_LABELS is None:
        CONTRACT_LABELS = load_or_create_contract_labels()
    return CONTRACT_LABELS

def load_or_create_contract_labels() -> ContractLabels:
    '''
    Load the contract labels from disk, or create a new one if it does not exist.
    '''
    contract_labels_path = get_contract_labels_path()
    if os.path.isfile(contract_labels_path):
        return ContractLabels.load(contract_labels_path)
    else:
        return ContractLabels()


def register_contract_label(address, label):
    '''
    Helper function to easily register a contract at a given address. If the contract is already registered, it is
    updated / merged with the new information.
    '''
    reg = contract_labels()
    reg.register_contract_label(address, label)

def contract_by_label(label):
    '''
    Helper function to easily get the address of a contract by label.
    '''
    reg = contract_labels()
    return reg.get_contract_address(label)

def labels_for_contract(address):
    '''
    Helper function to easily get the labels of a contract by address.
    '''
    reg = contract_labels()
    return reg.get_contract_labels(address)

def label_for_contract(address):
    '''
    Helper function to easily get a label of a contract by address.
    '''
    labels = labels_for_contract(address)
    if len(labels) == 0:
        return None
    return labels[0]
