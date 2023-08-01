#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from ethpwn import *

print("Current balance of wallets:")
for address, wallet in all_wallets().items():
    balance = wallet.balance()
    print(f"{wallet.name} [{wallet.address}]: {balance} [ {ether(balance)} ether ]")

if len(sys.argv) == 2:
    target_wallet = get_wallet(context.w3, sys.argv[1])
    assert target_wallet is not None, f"Could not find wallet {sys.argv[1]!r}"

    for address, wallet in all_wallets().items():
        if wallet.name == target_wallet.name:
            continue

        if ether(wallet.balance()) < 0.001:
            context.logger.info(f"Skipping {wallet.name} because it has {ether(wallet.balance())} < 0.001 ether")
            continue

        transfer_funds(address, target_wallet.address, None, private_key=wallet.private_key)