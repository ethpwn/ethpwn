
import json
from . import cmdline
from ..config import update_config
from ..config.wallets import Wallet, add_wallet

@cmdline
def import_wallets(wallets_file: str):
    '''
    Import wallets from a file. The file should be a JSON file with a list of wallet objects.
    '''
    with open(wallets_file) as f:
        wallets = json.load(f)
        wallets = [Wallet.from_json_dict(w) for w in wallets]
        import ipdb; ipdb.set_trace()
        for w in wallets:
            add_wallet(w)
        print(f"Imported {len(wallets)} wallets")
        update_config()


