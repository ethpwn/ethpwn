# Table of Contents

* [ethpwn.ethlib.contract\_metadata](#ethpwn.ethlib.contract_metadata)
  * [get\_language\_for\_compiler](#ethpwn.ethlib.contract_metadata.get_language_for_compiler)
  * [ContractMetadata](#ethpwn.ethlib.contract_metadata.ContractMetadata)
    * [from\_compiler\_output\_json](#ethpwn.ethlib.contract_metadata.ContractMetadata.from_compiler_output_json)
    * [to\_serializable](#ethpwn.ethlib.contract_metadata.ContractMetadata.to_serializable)
    * [from\_serializable](#ethpwn.ethlib.contract_metadata.ContractMetadata.from_serializable)
    * [language](#ethpwn.ethlib.contract_metadata.ContractMetadata.language)
    * [compiler\_name](#ethpwn.ethlib.contract_metadata.ContractMetadata.compiler_name)
    * [constructor\_source\_by\_id](#ethpwn.ethlib.contract_metadata.ContractMetadata.constructor_source_by_id)
    * [runtime\_source\_by\_id](#ethpwn.ethlib.contract_metadata.ContractMetadata.runtime_source_by_id)
    * [symbolic\_srcmap\_constructor](#ethpwn.ethlib.contract_metadata.ContractMetadata.symbolic_srcmap_constructor)
    * [symbolic\_srcmap\_runtime](#ethpwn.ethlib.contract_metadata.ContractMetadata.symbolic_srcmap_runtime)
    * [closest\_instruction\_index\_for\_constructor\_pc](#ethpwn.ethlib.contract_metadata.ContractMetadata.closest_instruction_index_for_constructor_pc)
    * [closest\_instruction\_index\_for\_runtime\_pc](#ethpwn.ethlib.contract_metadata.ContractMetadata.closest_instruction_index_for_runtime_pc)
    * [source\_info\_for\_constructor\_instruction\_idx](#ethpwn.ethlib.contract_metadata.ContractMetadata.source_info_for_constructor_instruction_idx)
    * [source\_info\_for\_runtime\_instruction\_idx](#ethpwn.ethlib.contract_metadata.ContractMetadata.source_info_for_runtime_instruction_idx)
    * [deploy](#ethpwn.ethlib.contract_metadata.ContractMetadata.deploy)
    * [deploy\_destructible](#ethpwn.ethlib.contract_metadata.ContractMetadata.deploy_destructible)
    * [get\_contract\_at](#ethpwn.ethlib.contract_metadata.ContractMetadata.get_contract_at)
    * [decode\_function\_input](#ethpwn.ethlib.contract_metadata.ContractMetadata.decode_function_input)
  * [ContractMetadataRegistry](#ethpwn.ethlib.contract_metadata.ContractMetadataRegistry)
    * [add\_solidity\_source](#ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.add_solidity_source)
    * [add\_solidity\_sources\_dict](#ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.add_solidity_sources_dict)
    * [add\_contracts\_from\_solidity\_files](#ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.add_contracts_from_solidity_files)
    * [add\_vyper\_source](#ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.add_vyper_source)
    * [add\_vyper\_sources\_dict](#ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.add_vyper_sources_dict)
    * [add\_contracts\_from\_vyper\_files](#ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.add_contracts_from_vyper_files)
    * [\_\_getitem\_\_](#ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.__getitem__)
    * [\_\_contains\_\_](#ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.__contains__)
    * [\_\_iter\_\_](#ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.__iter__)
    * [iter\_find](#ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.iter_find)
    * [find](#ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.find)
    * [iter\_find\_by\_name](#ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.iter_find_by_name)
    * [find\_by\_name](#ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.find_by_name)
    * [all\_contracts](#ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.all_contracts)

<a id="ethpwn.ethlib.contract_metadata"></a>

# ethpwn.ethlib.contract\_metadata

Module for everything to do with the contract metadata we have available.
Contains the metadata registry which is our knowledge base of all the contracts
we know about, and the `ContractMetadata` class which describes and holds that
metadata for a single contract.

<a id="ethpwn.ethlib.contract_metadata.get_language_for_compiler"></a>

#### get\_language\_for\_compiler

```python
def get_language_for_compiler(compiler)
```

Extract a language identifier from a given compiler json_output['compiler'] string.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadata"></a>

## ContractMetadata Objects

```python
class ContractMetadata(Serializable)
```

Holds all of the available metadata about a contract.
Includes the ABI, the bytecode, the source code, and the source map.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadata.from_compiler_output_json"></a>

#### from\_compiler\_output\_json

```python
@staticmethod
def from_compiler_output_json(compiler, source_file, contract_name,
                              output_json, input_sources, output_sources)
```

Constructs a ContractMetadata object for a contract in `source_file` with
name `contract_name` from the Compiler `output_json` and the `sources` dict.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadata.to_serializable"></a>

#### to\_serializable

```python
def to_serializable()
```

Returns a serializable dictionary representation of the object.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadata.from_serializable"></a>

#### from\_serializable

```python
@staticmethod
def from_serializable(value)
```

Loads a ContractMetadata object back from a serialized dictionary.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadata.language"></a>

#### language

```python
@property
def language() -> Union[Literal['vyper'], Literal['solidity']]
```

Based on the `compiler` property, return the language the given contract was written in.
Currently supports `vyper` and `solidity`.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadata.compiler_name"></a>

#### compiler\_name

```python
@property
def compiler_name() -> Union[Literal['vyper'], Literal['solc']]
```

Based on the `compiler` property, return the name of the compiler used to compile the
contract. Currently supports `vyper` and `solc`. Does not include version/commit information.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadata.constructor_source_by_id"></a>

#### constructor\_source\_by\_id

```python
def constructor_source_by_id(_id)
```

Looks up and returns the source code object for the given source id in the constructor code.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadata.runtime_source_by_id"></a>

#### runtime\_source\_by\_id

```python
def runtime_source_by_id(_id)
```

Looks up and returns the source code object for the given source id in the runtime code.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadata.symbolic_srcmap_constructor"></a>

#### symbolic\_srcmap\_constructor

```python
@property
def symbolic_srcmap_constructor()
```

Returns the symbolized source map for the constructor bytecode.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadata.symbolic_srcmap_runtime"></a>

#### symbolic\_srcmap\_runtime

```python
@property
def symbolic_srcmap_runtime()
```

Returns the symbolized source map for the runtime bytecode.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadata.closest_instruction_index_for_constructor_pc"></a>

#### closest\_instruction\_index\_for\_constructor\_pc

```python
def closest_instruction_index_for_constructor_pc(pc, fork='paris') -> int
```

Returns the index of the closest instruction in the constructor bytecode that is before
or at the given pc in the constructor bytecode.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadata.closest_instruction_index_for_runtime_pc"></a>

#### closest\_instruction\_index\_for\_runtime\_pc

```python
def closest_instruction_index_for_runtime_pc(pc, fork='paris') -> int
```

Returns the index of the closest instruction in the runtime bytecode that is before or at
the given pc in the runtime bytecode.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadata.source_info_for_constructor_instruction_idx"></a>

#### source\_info\_for\_constructor\_instruction\_idx

```python
def source_info_for_constructor_instruction_idx(
        insn_idx) -> InstructionSourceInfo
```

Returns the source info for instruction at index `insn_idx` in the constructor bytecode.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadata.source_info_for_runtime_instruction_idx"></a>

#### source\_info\_for\_runtime\_instruction\_idx

```python
def source_info_for_runtime_instruction_idx(insn_idx) -> InstructionSourceInfo
```

Returns the source info for instruction at index `insn_idx` in the runtime bytecode.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadata.deploy"></a>

#### deploy

```python
def deploy(*constructor_args, **tx_extras) -> Tuple[HexBytes, Contract]
```

Deploys a contract and registers it with the contract registry.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadata.deploy_destructible"></a>

#### deploy\_destructible

```python
@contextmanager
def deploy_destructible(*constructor_args, **tx_extras)
```

Deploys a `Destructible` contract and `destroy()`s it after the context manager exits
to retrieve any held funds. Utility function for quick one-off contracts so you can
easily get your funds back by default. The resulting deployed contract will also be
automatically registered with the contract registry.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadata.get_contract_at"></a>

#### get\_contract\_at

```python
def get_contract_at(addr) -> Contract
```

Returns a web3 contract instance for the contract at the given address. This will
automatically register the contract at the given address with the contract registry.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadata.decode_function_input"></a>

#### decode\_function\_input

```python
def decode_function_input(data)
```

Decodes the function input data for a contract of this class. Returns a tuple of the
function name and a dictionary of the arguments.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadataRegistry"></a>

## ContractMetadataRegistry Objects

```python
class ContractMetadataRegistry()
```

A registry containing all contracts and metadata for them that we know about. This is used
to retrieve information about deployed contracts, associate new contracts with their metadata,
and to retrieve metadata for contracts that are not deployed yet. This is the central point
for all contract-related metadata.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.add_solidity_source"></a>

#### add\_solidity\_source

```python
def add_solidity_source(source: str, file_name: Union[Path, str], **kwargs)
```

Compiles the given solidity source code and adds the resulting metadata
of all contracts to the registry.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.add_solidity_sources_dict"></a>

#### add\_solidity\_sources\_dict

```python
def add_solidity_sources_dict(sources: Dict[str, str], **kwargs)
```

Compiles the given solidity source dict `'sources'` in the input json and adds the
resulting metadata of all contracts to the registry.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.add_contracts_from_solidity_files"></a>

#### add\_contracts\_from\_solidity\_files

```python
def add_contracts_from_solidity_files(files: List[Union[str, Path]], **kwargs)
```

Compiles the given files and adds the resulting metadata of all contracts to the registry.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.add_vyper_source"></a>

#### add\_vyper\_source

```python
def add_vyper_source(source: str, file_name: Union[Path, str], **kwargs)
```

Compiles the given vyper source code and adds the resulting metadata
of all contracts to the registry.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.add_vyper_sources_dict"></a>

#### add\_vyper\_sources\_dict

```python
def add_vyper_sources_dict(sources: Dict[str, str], **kwargs)
```

Compiles the given vyper source dict `'sources'` in the input json and adds the
resulting metadata of all contracts to the registry.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.add_contracts_from_vyper_files"></a>

#### add\_contracts\_from\_vyper\_files

```python
def add_contracts_from_vyper_files(files: List[Union[str, Path]], **kwargs)
```

Compiles the given files and adds the resulting metadata of all contracts to the registry.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.__getitem__"></a>

#### \_\_getitem\_\_

```python
def __getitem__(key: Union[str, Tuple[str, str]]) -> ContractMetadata
```

Retrieve a contract's metadata either by `name` or by `(file_name, contract_name)`.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.__contains__"></a>

#### \_\_contains\_\_

```python
def __contains__(key: Union[str, Tuple[str, str]]) -> bool
```

Check if a contract's metadata is present either by `name` or by `(file_name, contract_name)`.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.__iter__"></a>

#### \_\_iter\_\_

```python
def __iter__()
```

Iterate over all contracts, yielding the file name, contract name, and metadata for each.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.iter_find"></a>

#### iter\_find

```python
def iter_find(predicate) -> Iterator[Tuple[str, str, ContractMetadata]]
```

Iterate over all contracts matching `predicate`, yielding the file name, contract name,
and metadata for each.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.find"></a>

#### find

```python
def find(predicate) -> Optional[Tuple[str, str, ContractMetadata]]
```

Find the first contract matching `predicate`, returning the file name, contract name,
and metadata.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.iter_find_by_name"></a>

#### iter\_find\_by\_name

```python
def iter_find_by_name(
        name: str) -> Iterator[Tuple[str, str, ContractMetadata]]
```

Iterate over all contracts with the given name, yielding the file name, contract name,
and metadata for each.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.find_by_name"></a>

#### find\_by\_name

```python
def find_by_name(name: str) -> Optional[Tuple[str, str, ContractMetadata]]
```

Find the first contract with the given name, returning the file name, contract name,
and metadata.

<a id="ethpwn.ethlib.contract_metadata.ContractMetadataRegistry.all_contracts"></a>

#### all\_contracts

```python
def all_contracts()
```

Iterate over all contracts, yielding the file name, contract name, and metadata for each.

