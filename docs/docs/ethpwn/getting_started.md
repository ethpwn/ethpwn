
`ethpwn` aims to solve a few tasks that users might commonly come in contact with.
To become acquainted with `ethpwn`, let's start by walking through several examples.

Similary to `pwntools`, `ethpwn` follows the “kitchen sink” approach.

```python
from ethpwn import *
```

This imports all you need to start compiling and interacting with smart contracts.

### 🐥 Tutorials

#### Compiling smart contracts

Smart contracts are usually written in high-level programming languages, most commonly [Solidity](https://soliditylang.org/) or sometimes [Vyper](https://vyper.readthedocs.io/en/stable/).

`ethpwn` provides a simple interface for compiling smart contracts and analyzing their compilation artifacts.

```python
>>> from ethpwn import *

>>> CONTRACT_METADATA.compile_solidity_files(['contract_a.sol', 'contract_b.sol'])
>>> contract_a = CONTRACT_METADATA['ContractA']
>>> print (f"ContractA: ABI: {contract_a.abi}")
>>> print (f"ContractA: deployed bytecode: {contract_a.bin_runtime}")
>>> print (f"ContractA: storage layout: {contract_a.storage_layout}")
>>> print (f"ContractA: source code for pc=0x1234: {contract_a.source_info_for_pc(0x1234)}")

>>> calldata = '0x12345678abcdef'
>>> func_name, args = contract_a.decode_function_input(calldata)
>>> print (f"ContractA: calldata calls function {func_name} with args {args}")
```

In addition to the compiled information accessible via the `ContractMetadata`, `ethpwn` also provides way to interact with deployed instances of a contract on the blockchain.

#### Deploying smart contracts

A contract instance can be retrieved either by deploying a new contract via `ContractMetadata.deploy()`, or by the address of an already deployed contract via `ContractMetadata.get_contract_at()`.

```python
# deploy an instance of ContractA onto the blockchain
# calls the contract's constructor with arguments 0, 1, and 2
>>> _, deployed_contract_a = contract_a.deploy(0, 1, 2)
>>> deployed_contract_a_address = deployed_contract_a.address
# get an instance of ContractA on the blockchain at the address obtained at the step before
>>> contract_a_instance = deployed_contract_a.get_contract_at(deployed_contract_a_address)
```

In both cases, `ethpwn` associates the address of the contract with the contract metadata by registering it in the [ContractRegistry](/ethpwn/ethpwn/global_state/#contractregistry) for future use.
The provided `Contract` instance can be used to interact with it using the [Web3py](https://web3py.readthedocs.io/en/stable/) API.

#### Interacting with smart contracts

`ethpwn`'s `transact()` is your one-stop shop for creating new transactions.
It estimates the gas costs of a transaction, checks that the funds necessary are available before launching it,
handles transactions reverting by simulating them first, etc.
Lastly, it automatically launches `ethdbg` to debug the transaction in case it fails or reverts. This feature can be enabled either by passing `debug_transaction_errors=True` to `transact()`, or, by setting the `debug_transaction_errors` flag in your `ethpwn` configuration (`ethpwn config debug_transaction_errors --set-to True`)

```python
# simulate the result of calling the `foo` function on the contract with arguments 0, 1, and 2
>>> result = contract_a_instance.functions.foo(0, 1, 2).call()

# create a transaction on the real blockchain calling the `foo` function on the contract with arguments 0, 1, and 2
>>> transact(contract_a_instance.functions.foo(0, 1, 2))

# create the same transaction, but ensure ethdbg is launched if the transaction fails or reverts
>>> transact(contract_a_instance.functions.foo(0, 1, 2), debug_transaction_errors=True)

# create a transaction with raw calldata
ccc = contract_registry().get(0x0AC6f85872C1e5309dEc61f94B10196ea1d248d0)
calldata = bytes.fromhex('30c13ade000000000001231031230102310230123')
transact(to=ccc.address, data=calldata, force=True)
```

#### Assembling and Disassembling EVM code

Easy API to assemble and disassemble EVM bytecode!

```python
>>> from ethpwn import *
>>> bytecode = assemble_pro("""
...   PUSH1 0x40
...   PC
...   PC
...   PC
...   PUSH1 0x00
...   PUSH1 0x01
...   SSTORE
... """)
>>> print(bytecode)
60405858586000600155
```

```python
>>> from ethpwn import *
>>> print(disassemble_pro('60405858586000600155'))
0000: 60 40        PUSH1 0x40          [gas=3, description="Place 1 byte item on stack."]
0002: 58           PC                  [gas=2, description="Get the value of the program counter prior to the increment."]
0003: 58           PC                  [gas=2, description="Get the value of the program counter prior to the increment."]
0004: 58           PC                  [gas=2, description="Get the value of the program counter prior to the increment."]
0005: 60 00        PUSH1 0x0           [gas=3, description="Place 1 byte item on stack."]
0007: 60 01        PUSH1 0x1           [gas=3, description="Place 1 byte item on stack."]
0009: 55           SSTORE              [gas=0, description="Save word to storage."]
```


#### Testing EVM bytecode on-the-fly

`pwnlib.runner.run_assembly` anyone? :)

```python
>>> from ethpwn import *
>>> bytecode = assemble_pro("PUSH1 0x40\nPC\nPC\nPC\nPUSH1 0x00\nPUSH1 0x01\nSSTORE\n")
>>> debug_shellcode(bytecode) # this will spawn an ethdbg session.
Debugger launched, press enter to continue...
```