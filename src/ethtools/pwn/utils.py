import functools
from hexbytes import HexBytes
from web3 import Web3
from .global_context import context

@functools.lru_cache(maxsize=1024)
def normalize_contract_address(address) -> str:
    """Normalize a contract address"""
    if not address:
        return None

    if type(address) == str:
        address = "0x" + address.replace("0x", '').zfill(40)

    if Web3.is_checksum_address(address):
        return address

    if type(address) == int:
        address = HexBytes(address.to_bytes(20, 'big'))

    return Web3.to_checksum_address(address)

def show_diff(a, b, show_old_new=False):
    from deepdiff import DeepDiff

    from rich import print
    from rich.table import Table

    """Show a diff between two objects"""
    diff = DeepDiff(a, b, ignore_order=True)
    table = Table(title="Diff")
    table.add_column("Type")
    table.add_column("Path")
    table.add_column("Diff")

    if show_old_new:
        table.add_column("Left")
        table.add_column("Right")

    for diff_type, diff_paths in diff.items():
        for diff_path, diff_value in diff_paths.items():
            table.add_row(diff_type, diff_path, diff_value['diff'])
    print(table)

def get_chain_name(id):
    if id == 1:
        return "mainnet"
    elif id == 11155111:
        return "sepolia"
    else:
        raise Exception("Unknown chain id")