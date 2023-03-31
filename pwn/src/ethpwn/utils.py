from hexbytes import HexBytes
from .global_context import context

def normalize_contract_address(address) -> str:
    """Normalize a contract address"""
    if not address:
        return None
    if isinstance(address, str):
        address = HexBytes(address)

    if len(address) != 20:
        raise ValueError(f'Invalid contract address: {address}')

    return context.w3.to_checksum_address(address)