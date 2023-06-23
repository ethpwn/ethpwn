import argparse
from typing import Dict

from hexbytes import HexBytes

from .. import config
from .. import contract_metadata
from .. import hashes
from ..global_context import context
from ..config import GLOBAL_CONFIG
from ..config.wallets import get_wallet

def parse_contract_addr(contract_addr):
    checksummed = context.w3.to_checksum_address(contract_addr)
    if checksummed != contract_addr:
        context.logger.warn(f"Contract address {contract_addr} is not checksummed, using {checksummed} instead")
    return checksummed

def main():
    wallets: Dict[Union[str, HexBytes]] = GLOBAL_CONFIG['wallets']
    wallet_options = ""
    default_wallet = None
    for addr, wallet in wallets.items():
        if default_wallet is None:
            default_wallet = wallet
        wallet_options += f"{wallet.name}({addr}),  "

    parser = argparse.ArgumentParser(description='Make a transaction to a contract')
    parser.add_argument('contract', help='The contract to call, can either be an address or a name', type=parse_contract_addr)
    parser.add_argument('selector', help='The function selector to call, can either be encoded as a hex string or a signature string')
    parser.add_argument('input', help='The input data to send as arguments, this will be eval()ed so you can use python syntax')
    parser.add_argument('--wallet', help=f'The wallet to send the transaction from, can be either a name or an address, if not specified the first wallet will be used (Options: {wallet_options})', default=default_wallet, type=get_wallet)
    parser.add_argument('--gas', help='The gas limit to use for the transaction', default=None, type=int)
    parser.add_argument('--gas-price', help='The gas price to use for the transaction', default=None, type=int)
    parser.add_argument('--value', help='The value to send with the transaction', default=None, type=int)
    parser.add_argument('--nonce', help='The nonce to use for the transaction', default=None, type=int)