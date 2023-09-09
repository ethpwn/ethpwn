import functools
import web3

from . import subcommand_callable, cmdline, rename
from ..config import update_config
from ..config.credentials import add_credentials_for

import json
from coolname import generate_slug

from . import cmdline
from ..currency_utils import ether
from ..config import update_config
from ..config.misc import get_default_network
from ..config.wallets import Wallet, add_wallet, all_wallets, get_wallet_by_address, get_wallet_by_name, get_wallet
from ..utils import get_chainid


wallet_handler = subcommand_callable(cmdline, 'wallet', __subcommand_doc='Manage wallets for ethlib')


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
def create(name: str=None, description=None, network=None, **kwargs):
    '''
    Create a new wallet and add it to the wallet registry.
    : FIXME
    '''

    if network:
        get_chainid(network) # validate the network name
    else:
        network = 'mainnet'

    if name is None:
        name = generate_slug()

    new_account = web3.Account.create()

    wallet = Wallet(new_account.address, new_account.key.hex(), name=name, description=description, network=network)
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

@wallet_handler
def balance(ident: str, network=None, **kwargs):
    '''
    Get the balance of a wallet.

    :param ident: the identifier of the wallet to retrieve, either the address or the name
    :param network: the network to get the balance on (default: mainnet)
    '''

    if network:
        get_chainid(network) # validate the network name
    else:
        network = get_default_network()

    wallet = get_wallet(ident, network)
    if wallet is None:
        raise ValueError(f"Wallet {ident} not found on {network}")
    balance = wallet.balance()
    print(f"Wallet {wallet.name} ({wallet.address}) on {wallet.network} has {ether(balance)} ether ({balance} wei)")
