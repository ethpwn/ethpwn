import json
import os

from ..user_input import input_bool, input_node_url, input_pick_choice_with_default, input_pick_from_list, input_wallet
from ..config import get_default_global_config_path, get_default_wallet_path, reload_default_config, save_config_as_default_config, update_config
from ..utils import get_chain_name
from ..global_context import context
from ..config.misc import set_default_node_url as _set_default_node_url, set_default_network as _set_default_network

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

    print("First, we need to know the ethereum nodes you'd like to use.")

    node_urls = {}
    while node_url := input_node_url(f'Ethereum node URL #{len(node_urls)}: '):
        context.connect_http(node_url)
        network = get_chain_name(int(context.w3.net.version))
        if network in node_urls:
            print(f'Node URL already added for network {network}. Please try again.')
            continue
        node_urls[network] = network

    print("Select the default network to use.")
    keys = list(node_urls.keys())
    index = input_pick_from_list(keys)
    network = keys[index]

    print("Next, we need to know the wallets you'd like to use.")
    wallets = []
    while True:
        wallet = input_wallet()
        wallets.append(wallet)
        if not input_bool("Add another wallet? "):
            break

    print("Select the default wallet to use.")
    default_index = input_pick_from_list(wallets)
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
def default_network(name: str = None, **kwargs):
    '''
    Set the default network to use
    '''
    if name is None:
        print(f"Current default network is {context.network}")
    else:
        context.network = name
        update_config()

@config_handler
def set_default_node_url(node_url: str, network: str=None, force: bool=False, **kwargs):
    '''
    Adds a default node URL to the context. If the node is not available, a warning is printed.
    All default node URLs are tried in order until one is available.
    '''
    success = context.connect_http(node_url, can_fail=True)
    if not success:
        if not force:
            context.logger.warning(
                'Refusing to set default node to %s because we were unable to connect to it.',
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
