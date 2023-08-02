
import json
import os
from typing import Dict, Iterator, List, Tuple

from hexbytes import HexBytes

from rich.table import Table

from .utils import normalize_contract_address
from .config import get_contract_names_path

class ContractNames:
    '''
    AMaps contract addresses to contract names.
    Serialized to the local configuration directory to ensure persistence across runs. This allows us to remember
    all contracts we've referred to by name in the past.

    In the future we plan on having a global name registry shared across all users of ethpwn that users can opt into.
    '''
    def __init__(self) -> None:
        # each contract can have multiple names, but each name can only refer to one contract
        self.address_to_names: Dict[str, List[str]] = {}
        self.name_to_address: Dict[str, str] = {}

    def register_contract_name(self, contract_address, contract_name):
        '''
        Name the given contract address with the given contract name.
        '''
        contract_address = normalize_contract_address(contract_address)

        assert contract_name not in self.name_to_address

        if contract_address in self.address_to_names:
            self.address_to_names[contract_address].append(contract_name)
        else:
            self.address_to_names[contract_address] = [contract_name]

        self.name_to_address[contract_name] = contract_address
        self.store(get_contract_names_path())

    def get_contract_names(self, contract_address) -> List[str]:
        '''
        Get the names registered for a given contract address.
        '''
        contract_address = normalize_contract_address(contract_address)
        return self.address_to_names.get(contract_address, [])

    def get_contract_address(self, contract_name) -> str:
        '''
        Get the address of the given contract name.
        '''
        return self.name_to_address.get(contract_name, None)

    def __iter__(self) -> Iterator[Tuple[str, str]]:
        return self.name_to_address.items().__iter__()

    def store(self, contract_names_path):
        '''
        Store the names to the given JSON file.
        '''

        with open(contract_names_path, "w") as f:
            json.dump({HexBytes(addr).hex(): names for addr, names in self.address_to_names.items()}, f, indent=2)

    @staticmethod
    def load(contract_names_path) -> 'ContractNames':
        '''
        Load the names from the given JSON path.
        '''
        if not os.path.isfile(contract_names_path):
            return False

        self = ContractNames()
        with open(contract_names_path, "r") as f:
            self.address_to_names = {normalize_contract_address(addr): names for addr, names in json.load(f).items()}
            self.name_to_address = {name: HexBytes(addr) for addr, names in self.address_to_names.items() for name in names}
        return self

    def __rich_console__(self, console, options):
        table = Table(title="Contract Names")
        table.add_column("Address")
        table.add_column("Name")
        for address, name in self.address_to_names.items():
            table.add_row(
                address,
                name
            )
        yield table



CONTRACT_NAMES: ContractNames = None
def contract_names() -> ContractNames:
    '''
    Get the global contract names. Loads the registry from disk if it is not already loaded.
    '''
    global CONTRACT_NAMES
    if CONTRACT_NAMES is None:
        CONTRACT_NAMES = load_or_create_contract_names()
    return CONTRACT_NAMES

def load_or_create_contract_names() -> ContractNames:
    '''
    Load the contract names from disk, or create a new one if it does not exist.
    '''
    contract_names_path = get_contract_names_path()
    if os.path.isfile(contract_names_path):
        return ContractNames.load(contract_names_path)
    else:
        return ContractNames()


def register_contract_name(address, name):
    '''
    Helper function to easily register a contract at a given address. If the contract is already registered, it is
    updated / merged with the new information.
    '''
    reg = contract_names()
    reg.register_contract_name(address, name)

def contract_by_name(name):
    '''
    Helper function to easily get the address of a contract by name.
    '''
    reg = contract_names()
    return reg.get_contract_address(name)

def names_for_contract(address):
    '''
    Helper function to easily get the names of a contract by address.
    '''
    reg = contract_names()
    return reg.get_contract_names(address)

def name_for_contract(address):
    '''
    Helper function to easily get a name of a contract by address.
    '''
    names = names_for_contract(address)
    if len(names) == 0:
        return None
    return names[0]
