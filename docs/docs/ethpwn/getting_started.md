
`ethpwn` aims to solve a few tasks that users might commonly come in contact with. 
To become acquainted with `ethpwn`, let's start by walking through several examples.

Similary to `pwntools`, `ethpwn` follows the “kitchen sink” approach.

```python
from ethpwn import *
```

This imports all you need to start compiling and interacting with smart contracts.

### 🐥 Tutorials

#### Compiling smart contracts

Smart contracts are most commonly written in high-level programming languages, most commonly [Solidity](https://soliditylang.org/) or sometimes [Vyper](https://vyper.readthedocs.io/en/stable/).

`ethpwn` provides a simple interface for compiling smart contracts, and programmatically access to the compiled artifacts.

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

Additionally to the compiled information accessible via the `ContractMetadata`, `ethpwn` also provides a `Contract` class which can be used to interact with contract instances on the blockchain.

#### Deploying smart contracts

A contract instance can be retrieved either by deploying a (new) given contract via `ContractMetadata.deploy()`, or by the address of an already deployed contract via `ContractMetadata.get_contract_at()`.

```python
# deploy an instance of ContractA onto the blockchain
# calls the contract's constructor with arguments 0, 1, and 2
>>> _, new_contract_address = contract_a.deploy(0, 1, 2)

# get an instance of ContractA on the blockchain at address 0x1234
>>> contract_a_instance = contract_a.get_contract_at(0x1234)
```

In both cases, `ethpwn` associates the address of the contract with the contract metadata, and provides a `Contract` instance which can be used to interact with the contract using the [Web3](https://web3py.readthedocs.io/en/stable/) API.

#### Interacting with smart contracts

`ethpwn`'s `transact()` is your one-stop shop for creating new transactions.
It estimates the gas costs of a transaction, checks that the funds necessary are available before launching it,
handles transactions reverting by simulating them first, etc.
In the future, it will be able to automatically launch `ethdbg` on the transaction to debug it in case of a revert.

```python
# simulate the result of calling the `foo` function on the contract with arguments 0, 1, and 2
>>> result = contract_a_instance.w3.foo(0, 1, 2).call()

# create a transaction on the real blockchain calling the `foo` function on the contract with arguments 0, 1, and 2
>>> transact(contract_a_instance.w3.foo(0, 1, 2))
```

#### Assembling and Disassembling EVM code

```python
>>> from ethpwn import *
>>> bytecode = assemble_pro("PUSH1 0x40\n PC\nPC\nPC\nPUSH1 0x00\nPUSH1 0x01\n SSTORE\n")
>>> print(bytecode) 
>>>'60405858586000600155'
```

```python
>>> from ethpwn import *
>>> disassemble_pro('60405858586000600155').split("\n")
```


#### Testing EVM bytecode on-the-fly

```python
>>> from ethpwn import *
>>> bytecode = assemble_pro("PUSH1 0x40\n PC\nPC\nPC\nPUSH1 0x00\nPUSH1 0x01\n SSTORE\n")
>>> run_shellcode(bytecode) # this will spawn an ethdbg session.
```