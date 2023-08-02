# Usage #

`ethpwn` aims to make interacting with the ethereum blockchain easier.
Specifically, when it comes to creating, deploying, and interacting with smart contracts, we found ourselves writing the same boilerplate code over and over again or performing such operations in a web browser (bleah!).
Comparing this to the state of binary exploitation in CTFs (where the awesome [pwntools](https://github.com/gallopsled/pwntools/) library is predominantly used to interact with a target program), a lot was left to be desired for web3 hacking.

`ethpwn` aims to be the `pwntools` for smart contracts, and provide a simple, easy to use interface for interacting with them.

The main 3 principles for `ethpwn` are:

1. allow integration of familiar smart contract technologies where appropriate to reduce the learning curve
2. provide a simple, consistent set of configuration that can simplify the process of interacting with smart contracts
3. prioritize concise, easy to use, high-level API which keeps the most common operations as simple as possible

## ⚙️ Installation

The main logic of `ethpwn` is written in Python, and can be installed via `pip`:

```bash
pip install ethpwn
```

Specifically, the core logic is found in the `ethpwn.ethlib` module, where the high-level API is found in `ethpwn.ethlib.prelude`.
For ease-of-use, this is also reexported in `ethpwn` itself, so that you can do `from ethpwn import *` to get convenient access
to the high-level API functionality.

## 🎯 Tasks

`ethpwn` aims to solve a few tasks that users might commonly come in contact with.

### Compiling and managing smart contracts

Smart contracts are most commonly written in high-level programming languages, most commonly [Solidity](https://soliditylang.org/) or sometimes [Vyper](https://vyper.readthedocs.io/en/stable/).

`ethpwn` provides a simple interface for compiling smart contracts, and programmatically access to the compiled artifacts.

```python
from ethpwn import *

CONTRACT_METADATA.compile_solidity_files(['contract_a.sol', 'contract_b.sol'])
ca = CONTRACT_METADATA['ContractA']
print (f"ContractA: ABI: {ca.abi}")
print (f"ContractA: deployed bytecode: {ca.bin_runtime}")
print (f"ContractA: storage layout: {ca.storage_layout}")
print (f"ContractA: source code for pc=0x1234: {ca.source_info_for_pc(0x1234)}")

calldata = '0x12345678abcdef'
func_name, args = contract_a.decode_function_input(calldata)
print (f"ContractA: calldata calls function {func_name} with args {args}")
```

Additionally to the compiled information accessible via the `ContractMetadata`, `ethpwn` also provides a `Contract` class which can be used to interact with contract instances on the blockchain.

A contract instance can be retrieved either by deploying a (new) given contract via `ContractMetadata.deploy()`, or by the address of an already deployed contract via `ContractMetadata.get_contract_at()`.

```python
# deploy an instance of ContractA onto the blockchain
# calls the contract's constructor with arguments 0, 1, and 2
_, new_contract_address = contract_a.deploy(0, 1, 2)

# get an instance of ContractA on the blockchain at address 0x1234
contract_a_instance = contract_a.get_contract_at(0x1234)
```

In both cases, `ethpwn` uses this information to associate the address of the contract with the contract metadata, and provides a `Contract` instance which can be used to interact with the contract using the [Web3](https://web3py.readthedocs.io/en/stable/) API.

```python
# simulate the result of calling the `foo` function on the contract with arguments 0, 1, and 2
result = contract_a_instance.w3.foo(0, 1, 2).call()

# create a transaction on the real blockchain calling the `foo` function on the contract with arguments 0, 1, and 2
transact(contract_a_instance.w3.foo(0, 1, 2))
```

`ethpwn`'s `transact()` is your one-stop shop for creating new transactions.
It estimates the gas costs of a transaction, checks that the funds necessary are available before launching it,
handles transactions reverting by simulating them first, etc.
In the future, it will be able to automatically launch `ethdbg` on the transaction to debug it in case of a revert.

