import argparse
from .. import config
from .. import contract_metadata
from .. import hashes
from ..global_context import context
from ..config import GLOBAL_CONFIG
from ..config.wallets import get_wallet_by_address, get_wallet_by_name

def main():
    parser = argparse.ArgumentParser(description='Decode a transactions input based on solidity interface')