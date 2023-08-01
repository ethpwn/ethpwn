
import json
from coolname import generate_slug

from . import cmdline
from ..config import update_config
from ..config.wallets import Wallet, add_wallet, all_wallets
from ..utils import get_chainid

@cmdline
def import_wallets(wallets_file: str, **kwargs):
    '''
    Import wallets from a file. The file should be a JSON file with a list of wallet objects.
    '''
    with open(wallets_file) as f:
        wallets = json.load(f)
        wallets = [Wallet.from_json_dict(w) for w in wallets]
        for w in wallets:
            add_wallet(w)
        print(f"Imported {len(wallets)} wallets")
        update_config()

@cmdline
def add_wallet(address: str, private_key: str, name: str=None, description=None, network=None, **kwargs):
    '''
    Add a wallet to the wallet registry.
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

@cmdline
def list_wallets(**kwargs):
    '''
    List the wallets in the wallet registry.
    '''
    for wallet in all_wallets().values():
        print(repr(wallet))
