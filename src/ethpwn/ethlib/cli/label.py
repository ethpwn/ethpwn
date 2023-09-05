
from hexbytes import HexBytes

from rich.table import Table

from ..utils import normalize_contract_address
from ..contract_labels import contract_labels, labels_for_contract, register_contract_label
from . import rename, subcommand_callable, cmdline


contracts_label_handler = subcommand_callable(cmdline, 'label', __subcommand_doc='Manage contract labels')

@contracts_label_handler
def add(label: str, address: HexBytes, **kwargs):
    '''
    Add a label for a contract address.
    '''
    register_contract_label(address, label)

@contracts_label_handler
def get(address: HexBytes, **kwargs):
    '''
    Get the labels of a contract address.
    '''
    return labels_for_contract(address)

@contracts_label_handler
@rename('list')
def _list(**kwargs):
    '''
    Show all contract labels.
    '''
    table = Table()
    table.add_column("Contract Address")
    table.add_column("Label")
    for label, address in contract_labels().label_to_address.items():
        table.add_row(
            normalize_contract_address(address),
            label
        )
    return table
