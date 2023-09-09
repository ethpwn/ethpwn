import json
import os
import web3

from coolname import generate_slug

from ..user_input import input_bool, input_node_url, input_pick_choice_with_default, input_pick_from_list, input_wallet, input_wallet_creation
from ..config import get_default_global_config_path, get_default_wallet_path, reload_default_config, save_config_as_default_config, update_config
from ..config.wallets import Wallet
from ..utils import get_chain_name
from ..global_context import context
from ..config.misc import get_default_node_url, set_default_node_url as _set_default_node_url, set_default_network as _set_default_network

from . import cmdline, subcommand_callable


config_handler = subcommand_callable(cmdline, 'config', __subcommand_doc='Manage config for ethlib')

@config_handler
def create(**kwargs):
    '''
    Create a new config file with a basic setup. Will interactively prompt you for the necessary information.
    '''
    config_path = get_default_global_config_path()
    wallet_path = get_default_wallet_path()
    if os.path.isfile(config_path) or os.path.isfile(wallet_path):
        if not input_bool(f'Config file {config_path} or wallet file {wallet_path} already exists. Are you sure you want to continue? '):
            return False

    print("""
          First, we need to know the ethereum nodes you'd like to use.
          If you don't have one yet, you can sign up for an account from Infura or Alchemy.
          Both services provide free-tier API keys that should be sufficient for most use cases.

          See https://infura.io/ or https://www.alchemy.com/
          Keep in mind that you will need separate API keys for each network you want to use, e.g. mainnet, sepolia, etc.
    """)

    node_urls = {}
    while node_url := input_node_url(f'Ethereum node URL #{len(node_urls)}'):
        context.connect(node_url)
        network = get_chain_name(int(context.w3.net.version))
        if network in node_urls:
            print(f'Node URL already added for network {network}. Please try again.')
            continue
        node_urls[network] = node_url

    if not node_urls:
        print('No node URLs specified. Please try again.')
        return False

    print("Select the default network to use.")
    keys = list(node_urls.keys())
    index = input_pick_from_list(keys) if len(keys) > 1 else 0
    network = keys[index]

    print("Next, we need to know the wallets you'd like to use.")
    wallets = []

    choice = input_wallet_creation("Do you want to create a new wallet or importing an existing one?")

    if choice == 'import':
        while True:
            wallet = input_wallet()
            wallets.append(wallet)
            if not input_bool("Add another wallet? "):
                break
    else:
        # ask user for a name for the wallet
        name = input("Wallet name? (optional): ")
        desc = input("Wallet description? (optional): ")

        if name is None:
            name = generate_slug()

        new_account = web3.Account.create()

        wallet = Wallet(new_account.address, new_account.key.hex(), name=name, description=desc, network=network)
        wallets.append(wallet)

    if not wallets:
        print('No wallets specified. Please try again.')
        return False

    print("Select the default wallet to use.")
    default_index = input_pick_from_list(wallets) if len(wallets) > 1 else 0
    default_wallet = wallets.pop(default_index)
    wallets.insert(0, default_wallet)

    print("Do you have an etherscan API key? This can be used to pull available verified source code for contracts you interact with. If so, enter it here. Otherwise, leave blank.")
    etherscan_api_key = input("Etherscan API key: ")
    if not etherscan_api_key.strip():
        etherscan_api_key = None

    debug_transaction_errors = input_bool("Would you like ethpwn to automatically spawn an ethdbg shell if a transaction fails?")

    config = {
        'default_network': network,
        'default_node_urls': node_urls,
        'credentials': {} if not etherscan_api_key else {'etherscan': etherscan_api_key},
        'wallets': {w.address: w for w in wallets},
        'debug_transaction_errors': debug_transaction_errors,
    }
    save_config_as_default_config(config)
    reload_default_config()

    return True

@config_handler
def default_network(set_to: str = None, **kwargs):
    '''
    Set or get the default network to use

    :param set_to: The network to set as default
    '''
    if set_to is None:
        print(f"Current default network is {context.network}")
    else:
        context.network = set_to
        update_config()


@config_handler
def debug_transaction_errors(set_to: bool = None, **kwargs):
    '''
    Set or get whether to automatically spawn an ethdbg shell if a transaction fails.

    :param set_to: Whether to automatically spawn an ethdbg shell if a transaction fails.
    '''
    if set_to is None:
        print(f"Current debug_transaction_errors is {context.debug_transaction_errors}")
    else:
        context.debug_transaction_errors = set_to
        update_config()


@config_handler
def set_default_node_url(node_url: str, network: str=None, force: bool=False, **kwargs):
    '''
    Sets the default node URL for `network`.

    If the node is not available, a warning is printed.
    If `force` is True, the node URL is set anyway.
    In case a node URL is already set for `network`, a warning is printed and the user is prompted to confirm the change.
    '''
    success = context.connect(node_url, can_fail=True)
    if not success:
        if not force:
            context.logger.warning(
                'Refusing to set default node to %r because we were unable to connect to it. Specify --force to override this.',
                node_url
            )
            return False
        else:
            assert network is not None, "You must specify a network when using --force in case we cannot auto-determine it from the node itself if we cannot connect"
            context.logger.warning(
                'Unable to connect to %s. Setting it anyway because --force was specified.',
                node_url
            )
    else:
        node_network = get_chain_name(int(context.w3.net.version))
        assert network is None or network == node_network, f"Node reports network {node_network}, but you specified {network}"
        network = node_network

    if prev_default := get_default_node_url(network):
        if prev_default == node_url:
            context.logger.info('Node URL %s is already the default for network %s', node_url, network)
            return False
        replace = input_bool(
            f'{prev_default!r} is currently the default node for network {network}. Are you sure you want to replace it with {node_url}? ')
        if not replace:
            return False
        else:
            context.logger.warning('Replacing default node URL %s for network %s with %s', prev_default, network, node_url)

    _set_default_node_url(node_url, network=network)
    update_config()
    return True

@config_handler
def show(**kwargs):
    '''
    Show the current config
    '''
    from ..config import GLOBAL_CONFIG
    return GLOBAL_CONFIG
