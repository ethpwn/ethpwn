
import json
import os
from pathlib import Path
from abc import ABC, abstractmethod

from ..serialization_utils import serialize_to_file

class EthtoolsConfigurable(ABC):
    @abstractmethod
    def get_serializable_config(self):
        raise NotImplementedError

    @abstractmethod
    def load_serialized_config(self, config):
        raise NotImplementedError

    @abstractmethod
    def relative_config_path(self) -> Path:
        raise NotImplementedError

    def store_config(self):
        path = pwn_config_root_dir() / self.relative_config_path()
        serialize_to_file(self.get_serializable_config(), path)

def pwn_config_root_dir() -> Path:
    dir = os.path.expanduser('~/.config/ethtools/pwn/')
    os.makedirs(dir, exist_ok=True)
    return Path(dir)

def dbg_config_root_dir():
    dir = os.path.expanduser('~/.config/ethtools/dbg/')
    os.makedirs(dir, exist_ok=True)
    return dir

def get_default_wallet_path() -> Path:
    return pwn_config_root_dir() / 'wallets.json'

def get_logged_deployed_contracts_dir() -> Path:
    d = pwn_config_root_dir() / 'deployed_contracts'
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_contract_registry_dir() -> Path:
    d = pwn_config_root_dir() / 'contract_registry'
    d.mkdir(parents=True, exist_ok=True)
    return d

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


