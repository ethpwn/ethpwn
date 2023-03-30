
import json
import os

def config_root_dir():
    return os.path.expanduser('~/.config/ethpwn')
def get_default_wallet_path():
    return config_root_dir() + '/wallets.json'

def get_default_verified_contracts_path():
    return config_root_dir() + "/export-verified-contractaddress-opensource-license.csv"

def get_logged_deployed_contracts_dir():
    return config_root_dir() + '/deployed_contracts/'

def get_contract_registry_dir():
    return config_root_dir() + '/contract_registry/'

def save_config(out_path):
    with open(out_path, 'w') as f:
        json.dump(GLOBAL_CONFIG, f)

def load_config(in_path, clear=True):
    with open(in_path, 'r') as f:
        loaded = json.load(f)
        if clear:
            GLOBAL_CONFIG.clear()
        GLOBAL_CONFIG.update(loaded)

def reload_default_config():
    GLOBAL_CONFIG.clear()
    GLOBAL_CONFIG.update(load_default_config())


def load_default_config():
    from .wallets import load_default_wallets
    return {
        'wallets': load_default_wallets(),
    }

GLOBAL_CONFIG = None
GLOBAL_CONFIG = load_default_config()

from . import wallets
from . import verified_contracts


