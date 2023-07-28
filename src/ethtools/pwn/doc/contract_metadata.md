<a id="ethtools.pwn.contract_metadata"></a>

# ethtools.pwn.contract\_metadata

Module for everything to do with the contract metadata we have available.
Contains the metadata registry which is our knowledge base of all the contracts
we know about, and the `ContractMetadata` class which describes and holds that
metadata for a single contract.

<a id="ethtools.pwn.contract_metadata.ContractMetadata"></a>

## ContractMetadata Objects

```python
class ContractMetadata(Serializable)
```

Holds all of the metadata about a contract class we have available.
Includes the ABI, the bytecode, the source code, and the source map.

<a id="ethtools.pwn.contract_metadata.ContractMetadata.from_solidity"></a>

#### from\_solidity

```python
@staticmethod
def from_solidity(source_file, contract_name, output_json, sources)
```

Constructs a ContractMetadata object for a contract in `source_file` with
name `contract_name` from the Compiler `output_json` and the `sources` dict.

<a id="ethtools.pwn.contract_metadata.ContractMetadata.to_serializable"></a>

#### to\_serializable

```python
def to_serializable()
```

Returns a serializable dictionary representation of the object.

<a id="ethtools.pwn.contract_metadata.ContractMetadata.from_serializable"></a>

#### from\_serializable

```python
@staticmethod
def from_serializable(value)
```

Loads a ContractMetadata object back from a serialized dictionary.

<a id="ethtools.pwn.contract_metadata.ContractMetadata.constructor_source_by_id"></a>

#### constructor\_source\_by\_id

```python
def constructor_source_by_id(_id)
```

Looks up and returns the source code object for the given source id in the constructor code.

<a id="ethtools.pwn.contract_metadata.ContractMetadata.runtime_source_by_id"></a>

#### runtime\_source\_by\_id

```python
def runtime_source_by_id(_id)
```

Looks up and returns the source code object for the given source id in the runtime code.

<a id="ethtools.pwn.contract_metadata.ContractMetadata.symbolic_srcmap_constructor"></a>

#### symbolic\_srcmap\_constructor

```python
@property
def symbolic_srcmap_constructor()
```

Returns the symbolized source map for the constructor bytecode.

<a id="ethtools.pwn.contract_metadata.ContractMetadata.symbolic_srcmap_runtime"></a>

#### symbolic\_srcmap\_runtime

```python
@property
def symbolic_srcmap_runtime()
```

Returns the symbolized source map for the runtime bytecode.

<a id="ethtools.pwn.contract_metadata.ContractMetadata.closest_instruction_index_for_constructor_pc"></a>

#### closest\_instruction\_index\_for\_constructor\_pc

```python
def closest_instruction_index_for_constructor_pc(pc, fork='paris') -> int
```

Returns the index of the closest instruction in the constructor bytecode that is before
or at the given pc in the constructor bytecode.

<a id="ethtools.pwn.contract_metadata.ContractMetadata.closest_instruction_index_for_runtime_pc"></a>

#### closest\_instruction\_index\_for\_runtime\_pc

```python
def closest_instruction_index_for_runtime_pc(pc, fork='paris') -> int
```

Returns the index of the closest instruction in the runtime bytecode that is before or at
the given pc in the runtime bytecode.

<a id="ethtools.pwn.contract_metadata.ContractMetadata.source_info_for_constructor_instruction_idx"></a>

#### source\_info\_for\_constructor\_instruction\_idx

```python
def source_info_for_constructor_instruction_idx(
        insn_idx) -> InstructionSourceInfo
```

Returns the source info for instruction at index `insn_idx` in the constructor bytecode.

<a id="ethtools.pwn.contract_metadata.ContractMetadata.source_info_for_runtime_instruction_idx"></a>

#### source\_info\_for\_runtime\_instruction\_idx

```python
def source_info_for_runtime_instruction_idx(insn_idx) -> InstructionSourceInfo
```

Returns the source info for instruction at index `insn_idx` in the runtime bytecode.

<a id="ethtools.pwn.contract_metadata.ContractMetadata.deploy"></a>

#### deploy

```python
def deploy(*constructor_args, **tx_extras) -> Tuple[HexBytes, Contract]
```

Deploys a contract and registers it with the contract registry.

<a id="ethtools.pwn.contract_metadata.ContractMetadata.deploy_destructible"></a>

#### deploy\_destructible

```python
@contextmanager
def deploy_destructible(*constructor_args, **tx_extras)
```

Deploys a `Destructible` contract and calls `destroy()` on it after the context manager exits
to retrieve any held funds. Utility function for quick one-off contracts so you can
easily get your funds back by default. The resulting deployed contract will also be
automatically registered with the contract registry.

<a id="ethtools.pwn.contract_metadata.ContractMetadata.get_contract_at"></a>

#### get\_contract\_at

```python
def get_contract_at(addr) -> Contract
```

Returns a web3 contract instance for the contract at the given address. This will
automatically register the contract at the given address with the contract registry.

<a id="ethtools.pwn.contract_metadata.ContractMetadata.decode_function_input"></a>

#### decode\_function\_input

```python
def decode_function_input(data)
```

Decodes the function input data for a contract of this class. Returns a tuple of the
function name and a dictionary of the arguments.

<a id="ethtools.pwn.contract_metadata.ContractMetadataRegistry"></a>

## ContractMetadataRegistry Objects

```python
class ContractMetadataRegistry()
```

A registry containing all contracts and metadata for them that we know about. This is used
to retrieve information about deployed contracts, associate new contracts with their metadata,
and to retrieve metadata for contracts that are not deployed yet. This is the central point
for all contract-related metadata.

<a id="ethtools.pwn.contract_metadata.ContractMetadataRegistry.add_solidity_source"></a>

#### add\_solidity\_source

```python
def add_solidity_source(source: str, file_name: Union[Path, str], **kwargs)
```

Compiles the given solidity source code and adds the resulting metadata
of all contracts to the registry.

<a id="ethtools.pwn.contract_metadata.ContractMetadataRegistry.add_contracts_from_solidity_files"></a>

#### add\_contracts\_from\_solidity\_files

```python
def add_contracts_from_solidity_files(files: List[Union[str, Path]], **kwargs)
```

Compiles the given files and adds the resulting metadata of all contracts to the registry.

<a id="ethtools.pwn.contract_metadata.ContractMetadataRegistry.iter_find"></a>

#### iter\_find

```python
def iter_find(predicate) -> Iterator[Tuple[str, str, ContractMetadata]]
```

Iterate over all contracts matching `predicate`, yielding the file name, contract name,
and metadata for each.

<a id="ethtools.pwn.contract_metadata.ContractMetadataRegistry.find"></a>

#### find

```python
def find(predicate) -> Optional[Tuple[str, str, ContractMetadata]]
```

Find the first contract matching `predicate`, returning the file name, contract name,
and metadata.

<a id="ethtools.pwn.contract_metadata.ContractMetadataRegistry.iter_find_by_name"></a>

#### iter\_find\_by\_name

```python
def iter_find_by_name(
        name: str) -> Iterator[Tuple[str, str, ContractMetadata]]
```

Iterate over all contracts with the given name, yielding the file name, contract name,
and metadata for each.

<a id="ethtools.pwn.contract_metadata.ContractMetadataRegistry.find_by_name"></a>

#### find\_by\_name

```python
def find_by_name(name: str) -> Optional[Tuple[str, str, ContractMetadata]]
```

Find the first contract with the given name, returning the file name, contract name,
and metadata.

<a id="ethtools.pwn.contract_metadata.ContractMetadataRegistry.all_contracts"></a>

#### all\_contracts

```python
def all_contracts()
```

Iterate over all contracts, yielding the file name, contract name, and metadata for each.

