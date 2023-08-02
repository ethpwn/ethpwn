import functools
from . import subcommand_callable, cmdline, rename
from ..config import update_config
from ..config.credentials import add_credentials_for

import json
from coolname import generate_slug

from . import cmdline
from ..config import update_config
from ..config.wallets import Wallet, add_wallet, all_wallets
from ..utils import get_chainid


wallet_handler = subcommand_callable(cmdline, 'wallet', doc='Manage wallets for ethlib')


@wallet_handler
@rename('import')
def _import(wallets_file: str, **kwargs):
    '''
    Import wallets from a file. The file should be a JSON file with a list of wallet objects.

    :param wallets_file: the JSON file to import the wallets from
    '''
    with open(wallets_file) as f:
        wallets = json.load(f)
        wallets = [Wallet.from_json_dict(w) for w in wallets]
        for w in wallets:
            add_wallet(w)
        print(f"Imported {len(wallets)} wallets")
        update_config()

@wallet_handler
def add(address: str, private_key: str, name: str=None, description=None, network=None, **kwargs):
    '''
    Add a wallet to the wallet registry.

    :param address: the address of the wallet
    :param private_key: the private key of the wallet
    :param name: the name of the wallet
    :param description: the description of the wallet
    :param network: the network the wallet is on
    '''
    if network:
        get_chainid(network) # validate the network name
    else:
        network = 'mainnet'

    if name is None:
        name = generate_slug()

    wallet = Wallet(address, private_key, name=name, description=description, network=network)
    add_wallet(wallet)
    update_config()
    return wallet

@wallet_handler
@rename('list')
def _list(**kwargs):
    '''
    List the wallets in the wallet registry.
    '''
    for wallet in all_wallets().values():
        print(repr(wallet))
