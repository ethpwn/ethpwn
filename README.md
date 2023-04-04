# ethtools
Tooling to make interacting with the Ethereum ecosystem less painful

# INSTALL 

```
1. git clone git@github.com:shellphish/ethtools.git && pip install -e ethtools/pwn
2. touch ~/.config/ethtools/wallets.json

The wallets.json file should be:

[
  {
    "name": "sepolia",
    "network": "sepolia",
    "address": "",
    "private_key": "",
    "description": ""
  },
  {
    "name": "mainnet",
    "network": "mainnet",
    "address": "",
    "private_key": "",
    "description": ""
  }
]
```


# ethdbg Usage

Replay a transaction:
```
ethdbg.py --txid 0xc6e3666c0347e2362b61db5c27ae9e76dac5b48e1e2d0e6cf586c6594e940d3b
```

Replay a transaction with specific wallet
```
ethdbg.py --txid 0xc6e3666c0347e2362b61db5c27ae9e76dac5b48e1e2d0e6cf586c6594e940d3b --wallet sepolia
```

Replay a transaction as another sender:
```
ethdbg.py --txid 0xc6e3666c0347e2362b61db5c27ae9e76dac5b48e1e2d0e6cf586c6594e940d3b --sender 0x76cf6361F21dB7A36eAa88649FEeBD9F18d94647
```

Simulate a new transaction:

```
ethdbg.py -- --target 0xeC55Bf7E10b6594874554BAd1B461214Cab413d4 --calldata cbd8c06a00000000000000
```

Simulate a new transaction at specific block:
```
ethdbg.py -- --target 0xeC55Bf7E10b6594874554BAd1B461214Cab413d4 --calldata cbd8c06a00000000000000 --block 11469711
```

