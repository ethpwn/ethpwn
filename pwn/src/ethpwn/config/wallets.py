import json
import os
from typing import Dict

from ..global_context import context

class Wallet:
    def __init__(self, address=None, private_key=None, name=None, description=None, network=None):
        self.address = address
        self.private_key = private_key
        self.name = name
        self.description = description
        self.network = network

    def __repr__(self) -> str:
        return f"Wallet(address={self.address!r}, private_key=<blinded>, name={self.name!r}, description={self.description!r}, network={self.network!r})"

    def balance(self):
        return context.w3.eth.get_balance(self.address)

    def to_string_repr(self) -> str:
        return f"{self.address}:{self.private_key}:{self.name}:{self.description}:{self.network}"

    def __str__(self) -> str:
        return self.__repr__()

    def from_json_dict(d):
        return Wallet(**d)

    def to_serializable_dict(self):
        return {
            'address': self.address,
            'private_key': self.private_key,
            'name': self.name,
            'description': self.description,
            'network': self.network,
        }

    def from_string_repr(repr, default_name=None, default_description=None):
        if default_name is None:
            default_name = lambda address, priv_key: f"Account {address}"
        if default_description is None:
            default_description = lambda address, priv_key: f"Account {address}"
        split = repr.split(":")
        if len(split) == 2:
            split.append(default_name(*split))
        if len(split) == 3:
            split.append(default_description(*split[:2]))
        if len(split) == 4:
            split.append("sepolia")
        address, private_key, name, description, network = split
        assert network == "sepolia", "You should only ever use testnet accounts for the love of god."
        return Wallet(address, private_key, name, description)


def load_default_wallets():
    wallets_config_path = get_default_wallet_path()
    os.makedirs(os.path.dirname(wallets_config_path), exist_ok=True)
    if not os.path.exists(wallets_config_path):
        with open(wallets_config_path, 'w') as f:
            f.write('[]')

    with open(wallets_config_path, 'r') as f:
        result = json.load(f)
    result = {d['address']: Wallet.from_json_dict(d) for d in result}

    if os.environ.get('ETHPWN_ACCOUNTS', None) is not None:
        for account in os.environ['ETHPWN_ACCOUNTS'].split(';'):
            result.add(Wallet.from_string_repr(account))

    if os.environ.get("ETHADDRESS", None) and os.environ.get("ETHPRIVATEKEY", None):
        addr, priv_key = os.environ['ETHADDRESS'], os.environ['ETHPRIVATEKEY']
        result.add(Wallet.from_string_repr(f"{addr}:{priv_key}"))
        result[os.environ['ETHADDRESS']] = os.environ['ETHPRIVATEKEY']

    return result

def add_default_wallet(address, private_key):
    from . import GLOBAL_CONFIG
    accounts = load_default_wallets()
    if address not in accounts or accounts[address] != private_key:
        accounts[address] = private_key
        with open(GLOBAL_CONFIG['wallets'], 'w') as f:
            json.dump(accounts, f)
    add_wallet(address, private_key)

def add_wallet(address, private_key):
    from . import GLOBAL_CONFIG
    assert address not in GLOBAL_CONFIG['wallets'] or GLOBAL_CONFIG['wallets'][address] == private_key, "Account already exists with different private key, likely a mistake."
    GLOBAL_CONFIG['wallets'][address] == private_key

def get_wallet_by_address(address) -> Wallet:
    from . import GLOBAL_CONFIG
    return GLOBAL_CONFIG['wallets'].get(address, None)

def get_wallet_by_name(name) -> Wallet:
    from . import GLOBAL_CONFIG
    for address, wallet in GLOBAL_CONFIG['wallets'].items():
        if wallet.name == name:
            return wallet
    return None

def all_wallets() -> Dict[str, Wallet]:
    from . import GLOBAL_CONFIG
    return GLOBAL_CONFIG['wallets'].copy()

def get_wallet(address_or_name) -> Wallet:
    from . import GLOBAL_CONFIG
    if address_or_name is None:
        return next(iter(GLOBAL_CONFIG['wallets'].values()), None)
    if wallet := get_wallet_by_name(address_or_name):
        return wallet
    if wallet := get_wallet_by_address(address_or_name):
        return wallet
    return None



def delete_wallet(address):
    from . import GLOBAL_CONFIG
    if address in GLOBAL_CONFIG['wallets']:
        del GLOBAL_CONFIG['wallets'][address]

def delete_default_wallet(address):
    accounts = load_default_wallets()
    if address in accounts:
        del accounts[address]
        with open(get_default_wallet_path(), 'w') as f:
            json.dump(accounts, f)
    delete_wallet(address)


from . import get_default_wallet_path