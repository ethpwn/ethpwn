from .config.wallets import Wallet
from .utils import get_chain_name, normalize_contract_address
from .global_context import context
from web3 import Web3
from hexbytes import HexBytes

def input_until_valid(prompt, invalid_reason, stop_on_blank=True):
    while True:
        value = input(prompt + " (leave blank to cancel): " if stop_on_blank else prompt + ": ")
        if not value.strip():
            if stop_on_blank:
                return None
        reason = None
        try:
            reason = invalid_reason(value)
        except Exception as ex:
            reason = f"Failed to parse input: {ex}"
        if reason:
            print(reason)
            continue

        return value

def input_pick_choice(prompt, choices, parse=str):
    def invalid_reason(value):
        value = parse(value)
        if value not in choices:
            return f"Invalid value: {value} must be one of {choices}"
    return input_until_valid(prompt, invalid_reason)


def input_pick_choice_with_default(prompt, choices, default, parse=str):
    def invalid_reason(value):
        if not value.strip():
            return None
        value = parse(value)
        if value not in choices:
            return f"Invalid value: {value} must be one of {choices}"

    return input_until_valid(prompt, invalid_reason) or default

def input_pick_from_list(choices, repr_func=repr):
    for i, choice in enumerate(choices):
        print(f"{i}: {repr_func(choice)}")

    def invalid_reason(value):
        try:
            value = int(value)
        except ValueError:
            return f"{value} must be an integer"
        if value < 0 or value >= len(choices):
            return f"{value} must be between 0 and {len(choices)-1}"

    return int(input_until_valid("Pick a choice: ", invalid_reason))

def _reason_invalid_node_url(value):
    if not value.strip():
        return None # empty is fine

    try:
        if value.startswith("http://") or value.startswith("https://"):
            provider = Web3.HTTPProvider(value)
        elif value.startswith("ws://") or value.startswith("wss://"):
            provider = Web3.WebsocketProvider(value)
        else:
            provider = Web3.IPCProvider(value)

        web3 = Web3(provider)
        if web3.is_connected():
            return None
        else:
            return "Could not connect to node URL"
    except Exception as ex:
        return f"Could not connect to node URL: {ex}"

def _reason_invalid_address(value):
    if not value.strip():
        return "Address cannot be empty"

    normalized = normalize_contract_address(value)
    if not normalized:
        return "Invalid address: normalization failed"

    if not Web3.is_address(value):
        return "Invalid address"

    return None

def _reason_invalid_private_key(value):
    if not value.strip():
        return "Private key cannot be empty"

    value = HexBytes(value)
    if not value:
        return "Invalid private key"

    if len(value) > 32:
        return "Private key too long"

    return None


def _parse_failure(func):
    def _try_parse(value):
        try:
            x = func()
            return None
        except Exception as ex:
            return f"Failed to parse input: {ex}"
    return _try_parse

def input_node_url(prompt):
    return input_until_valid(prompt, _reason_invalid_node_url)

def input_network(prompt):
    return input_pick_choice(prompt, ["mainnet", "sepolia"], parse=lambda x: x.lower())

def input_bool(prompt):
    return input_pick_choice(prompt + " [y/n] ", ["y", "n"], parse=lambda x: x.lower()) == 'y'

def input_wallet():
    # first, should we create a new wallet or use an existing one?
    do_import = input_bool("Import existing wallet? ")

    w3 = context.w3
    if do_import:
        address = input_until_valid("Address", _reason_invalid_address, stop_on_blank=False)
        private_key = input_until_valid("Private key", _reason_invalid_private_key, stop_on_blank=False)
        network = input_network("Network: ")
    else:
        new_user = w3.eth.account.create()
        address = new_user.address
        private_key = new_user.key.hex()
        network = get_chain_name(w3.eth.chain_id)

    name = input("Name (should be unique, leave empty to automatically name): ") or f"Wallet {network} - {address}"
    description = input("Description (optional): ")

    return Wallet(address, private_key, name, description, network)

