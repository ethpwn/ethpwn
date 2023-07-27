
def get_disable_autoconnect():
    '''
    Get whether autoconnect is disabled
    '''
    from . import GLOBAL_CONFIG
    return GLOBAL_CONFIG.get('disable_autoconnect', False)

def get_default_network():
    '''
    Get the default network
    '''
    from . import GLOBAL_CONFIG
    return GLOBAL_CONFIG.get('default_network', None)

def get_default_node_url_for_network(network='mainnet'):
    '''
    Get the default node URL for the given network.
    '''
    from . import GLOBAL_CONFIG
    return GLOBAL_CONFIG.get('default_node_urls', {}).get(network, None)
