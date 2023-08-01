import json
from ..config import update_config
from ..utils import get_chain_name
from ..global_context import context
from ..config.misc import set_default_node_url as _set_default_node_url

from . import cmdline

@cmdline
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

@cmdline
def show_config(**kwargs):
    '''
    Show the current config
    '''
    from ..config import GLOBAL_CONFIG
    return GLOBAL_CONFIG
