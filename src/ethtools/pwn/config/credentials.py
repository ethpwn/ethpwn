
import os


def get_credentials_for(service):
    from . import GLOBAL_CONFIG
    if 'credentials' not in GLOBAL_CONFIG:
        GLOBAL_CONFIG['credentials'] = {}
    return GLOBAL_CONFIG['credentials'].get(service, None)

def add_credentials_for(service, creds):
    from . import GLOBAL_CONFIG
    if 'credentials' not in GLOBAL_CONFIG:
        GLOBAL_CONFIG['credentials'] = {}
    GLOBAL_CONFIG['credentials'][service] = creds

def get_etherscan_api_key(api_key=None):
    from . import GLOBAL_CONFIG
    if api_key is None:
        api_key = os.environ.get('ETHERSCAN_API_KEY', None)
    if api_key is None:
        api_key = get_credentials_for('etherscan')
    return api_key
