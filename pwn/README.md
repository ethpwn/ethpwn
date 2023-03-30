# ethpwn

A tool to help with ethereum smart contract exploit interaction, designed with CTF challenges in mind.
One might call it a set of pwn tools for ethereum exploitation :P. ethpwn is designed to help you waste the smallest amount
of time possible on the annoying parts of interacting with ethereum smart contracts, mainly deployment, transaction sending,
and interaction.

## Installation

```bash
pip install ethpwn
```

## Usage

### Example exploits for the ethernaut challenges

SPOILERS AHEAD! If you haven't solved the ethernaut challenges yet, you should solve them first before looking at the
respective examples.

With that said, you can see examples of how to use `ethpwn` to solve the ethernaut challenges in the [Lukas-Dresel/ethernaut](https://github.com/Lukas-Dresel/ethernaut) repository. This illustrates various versions of using `ethpwn` to make exploitation easy.

Some examples are how to make import from openzeppelin work (see exploit_onchain.py), how to move funds from different
test wallets (see consolidate_ctf_funds_into.py)

### Deploying an exploit contract

```python
#!/usr/bin/env python3

import os
import sys
from time import sleep
from ethpwn.prelude import *


context.connect_http(sys.argv[1])

# syntax deploy.py <contract to deploy> [<solidity files with code..>]
CONTRACT_METADATA.add_solidity_files(sys.argv[2:])

with CONTRACT_METADATA['Exploit'].deploy_destructible() as (tx_hash, target):

    print(f"Exploit contract is at {target.address}")

    transact(target.functions.exploit(), value=ARGS.value, force=ARGS.force)

    # on __exit__ of the context manager, `contract.destroy()` will be called to return any leftover funds
```

### Interacting with the target contract to exploit it off-chain

An example of how to interact with the target contract to exploit it off-chain can be found in the `examples/` directory.

SPOILER ALERT: This example is the solution to the ethernaut fallback challenge.

The gist of it looks as follows:

```python
...

# illustration of how to import contracts from strings
CONTRACT_SOURCE=""" <copy & paste the source from ethernaut here> """
CONTRACT_METADATA.add_solidity_source(CONTRACT_SOURCE, 'Fallback.sol')

target = CONTRACT_METADATA['Fallback'].get_contract_at(ARGS.target_addr)

# set our contribution to non-zero
transact(target.functions.contribute(), value=wei(ether=0.0001))
```