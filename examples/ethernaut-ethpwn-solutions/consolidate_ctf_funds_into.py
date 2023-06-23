#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from ethpwn.prelude import *

context.connect_http(sys.argv[1])

print("Current balance of wallets:")
for address, wallet in all_wallets():
    balance = wallet.balance()
    print(f"{wallet.name} [{wallet.address}]: {balance} [ {ether(balance)} ether ]")

if len(sys.argv) == 2:
    target_wallet = get_wallet(sys.argv[1])
    assert target_wallet is not None, f"Could not find wallet {sys.argv[1]!r}"

    for address, wallet in all_wallets():
        if wallet.name == target_wallet.name:
            continue

        if ether(wallet.balance()) < 0.001:
            context.logger.info(f"Skipping {wallet.name} because it has {ether(wallet.balance())} < 0.001 ether")
            continue

        transfer_funds(address, target_wallet.address, None, private_key=wallet.private_key)