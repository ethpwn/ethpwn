# About ethpwn #

`ethpwn` aims to make interacting with the Ethereum blockchain easier.
Specifically, when it comes to creating, deploying, and interacting with smart contracts, we found ourselves writing the same boilerplate code over and over again or performing such operations in a web browser (bleah!).
Comparing this to the state of binary exploitation in CTFs (where the awesome [pwntools](https://github.com/gallopsled/pwntools/) library is predominantly used to interact with a target program), a lot was left to be desired for web3 hacking.

`ethpwn` aims to be the `pwntools` for smart contracts, and provide a simple, easy to use interface for interacting with them.

The main 3 principles for `ethpwn` are:

1. allow integration of familiar smart contract technologies where appropriate to reduce the learning curve
2. provide a simple, consistent set of configuration that can simplify the process of interacting with smart contracts
3. prioritize concise, easy to use, high-level API which keeps the most common operations as simple as possible

## ⚙️ Installation

The main logic of `ethpwn` is written in Python3, and can be installed via `pip`:

```bash
pip install ethpwn
```

Specifically, the core logic is found in the `ethpwn.ethlib` module, where the high-level API is found in `ethpwn.ethlib.prelude`.
For ease-of-use, this is also reexported in `ethpwn` itself, so that you can do `from ethpwn import *` to get convenient access
to the high-level API functionality.


| ❗️ Note                                                              |
|----------------------------------------------------------------------|
<<<<<<< Updated upstream
| To start out, if you haven't created your global config before, you should run `ethpwn config create` to generate your initial configuration file. This command will interactively prompt you for the most important settings, including the Ethereum node URL to use and wallets you want to use. |
=======
| To start out, if you haven't created your global config before, you should run `ethpwn config create` to generate your initial configuration file. This command will interactively prompt you for the most important settings, including the Ethereum node URL to use and wallets you want to use. |
>>>>>>> Stashed changes
