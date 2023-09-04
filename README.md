# ethpwn 🐛 ⚔️

[![PyPI](https://img.shields.io/pypi/v/ethpwn?style=flat)](https://pypi.org/project/ethpwn/)
[![License](https://img.shields.io/github/license/Ileriayo/markdown-badges?style=flat)]([https://pypi.org/project/ethpwn/](https://raw.githubusercontent.com/ethpwn/ethpwn/main/LICENSE))
[![Docs](https://img.shields.io/badge/Documentation-gh_pages)](https://ethpwn.github.io/ethpwn/)

`ethpwn` is a project inspired by the widely popular CTF exploitation framework pwntools, and the amazing enhanced GDB utility GEF. In other words, ethpwn is all you ever wanted for debugging and interacting with smart contracts on EVM-based blockchains.

More practically, this package includes a kick-ass command line debugger for simulating and re-playing Ethereum transactions (`ethdbg`), and a set of convenient wrappers for many `web3` functionalities that are useful for interacting with smart contracts.


![](./docs/docs/imgs/598565.gif)

## ⚡️ Quick Setup ##

#### Release Installation
```bash
pip install ethpwn
```

#### Developer Installation
Make sure your pip version is >= 23.1.2, then:
```bash
git clone git@github.com:ethpwn/ethpwn.git && cd ./ethpwn && pip install -e .
```


## ⚡️ Jump Start for ethdbg ##
```bash
ethdbg --txid 0x82a11757c3f34c2882e209c6e5ae96aff3e4db7f7984d54f92b02e1fed87e834 --node-url https://mainnet.infura.io/v3/38eb4be006004da4a89315232040e222
```

## 📖 Documentation ##
[![Docs](https://img.shields.io/badge/Documentation-gh_pages)](https://ethpwn.github.io/ethpwn/)


## ⚙️ Currently Supported EVM-based Chains ##

| Chain Name | Chain Id | Supported |
|-------------------|----------|----------|
| mainnet | 1 | ✅ |
| sepolia (testnet) | 11155111 | ✅ |

