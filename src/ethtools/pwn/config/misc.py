
def get_disable_autoconnect():
    '''
    Get whether autoconnect is disabled
    '''
    from . import GLOBAL_CONFIG
    return GLOBAL_CONFIG.get('disable_autoconnect', False)

def set_disable_autoconnect(value):
    '''
    Set whether autoconnect is disabled
    '''
    from . import GLOBAL_CONFIG, update_default_config
    GLOBAL_CONFIG['disable_autoconnect'] = value
    update_default_config()

def get_default_network():
    '''
    Get the default network
    '''
    from . import GLOBAL_CONFIG
    return GLOBAL_CONFIG.get('default_network', 'mainnet')

def set_default_network(network):
    '''
    Set the default network
    '''
    from . import GLOBAL_CONFIG, update_default_config
    assert network in ['mainnet', 'ropsten', 'rinkeby', 'goerli', 'kovan', 'sepolia']
    GLOBAL_CONFIG['default_network'] = network
    update_default_config()

def get_default_node_url_for_network(network='mainnet'):
    '''
    Get the default node URL for the given network.
    '''
    from . import GLOBAL_CONFIG
    return GLOBAL_CONFIG.get('default_node_urls', {}).get(network, None)

def set_default_node_url(node_url, network='mainnet'):
    '''
    Set the default node URL for the given network.
    '''
    from . import GLOBAL_CONFIG, update_default_config
    GLOBAL_CONFIG['default_node_urls'][network] = node_url
    update_default_config()
