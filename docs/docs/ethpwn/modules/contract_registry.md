<a id="ethpwn.ethlib.contract_registry"></a>

# ethpwn.ethlib.contract\_registry

<a id="ethpwn.ethlib.contract_registry.best_effort_get_contract_address_and_tx_hash_and_receipt"></a>

#### best\_effort\_get\_contract\_address\_and\_tx\_hash\_and\_receipt

```python
def best_effort_get_contract_address_and_tx_hash_and_receipt(
        contract_address=None, tx_hash=None, tx_receipt: TxReceipt = None)
```

Takes any combination of contract_address, tx_hash, tx_receipt and returns a tuple of (contract_address, tx_hash, tx_receipt)

as best as can be found. E.g. with only a contract address we currently have no way of obtaining the `tx_hash` and `tx_receipt`.
However, with either of the two we can obtain all three.

**Arguments**:

- `contract_address`: The address of the contract
- `tx_hash`: The transaction hash of the transaction that deployed the contract
- `tx_receipt`: The transaction receipt of the transaction that deployed the contract

**Returns**:

A tuple of (contract_address, tx_hash, tx_receipt)

<a id="ethpwn.ethlib.contract_registry.ContractInstance"></a>

## ContractInstance Objects

```python
class ContractInstance(Serializable)
```

Represents a contract that has been deployed to the blockchain. Binds a contract address to its metadata, associated transaction hash and receipt, and the deployment wallet if it was self-deployed by ethpwn (e.g. via `deploy`).

<a id="ethpwn.ethlib.contract_registry.ContractInstance.to_serializable"></a>

#### to\_serializable

```python
def to_serializable()
```

**Returns**:

A dictionary that can be serialized to JSON

<a id="ethpwn.ethlib.contract_registry.ContractInstance.w3"></a>

#### w3

```python
def w3()
```

Get a web3 contract object for this contract. Automatically has the correct ABI based on the metadata.

**Returns**:

The web3 contract object

<a id="ethpwn.ethlib.contract_registry.ContractInstance.merge"></a>

#### merge

```python
def merge(other: 'ContractInstance') -> bool
```

Merge the given contract into this contract. Ensures changes are compatible, e.g. if the address is already set, it cannot be changed. Information can only be added. See `update()` for more details.

<a id="ethpwn.ethlib.contract_registry.ContractInstance.update"></a>

#### update

```python
def update(address=None,
           metadata=None,
           deploy_tx_hash=None,
           deploy_tx_receipt=None,
           deploy_wallet=None) -> bool
```

Update this contract with the given values. If a value is None, it is left unchanged. Ensures changes are compatible,

e.g. if the address is already set, it cannot be changed. Information can only be added.

**Arguments**:

- `address`: The address of the contract
- `metadata`: The metadata of the contract
- `deploy_tx_hash`: The transaction hash of the transaction that deployed the contract
- `deploy_tx_receipt`: The transaction receipt of the transaction that deployed the contract
- `deploy_wallet`: The wallet that deployed the contract

**Returns**:

True if any value was changed, False otherwise

<a id="ethpwn.ethlib.contract_registry.ContractRegistry"></a>

## ContractRegistry Objects

```python
class ContractRegistry()
```

A registry of contracts. Maps contract addresses to contract objects which hold metadata, transaction hash
and receipt, and the deployment wallet of each contract (if self-deployed by ethpwn (e.g. via `deploy`).

Serialized to the local configuration directory to ensure persistence across runs. This allows us to remember contracts
we've deployed in the past, and also to remember contracts we've interacted with in the past (e.g. via `call`,
`transact` or seen in `ethdbg`).

In the future we plan on having a global contract registry that is shared across all users of ethpwn that users
can opt into. This will allows us to collect a superset of verified contracts that can be used to automatically
populate the local contract registry if the user did not have them available locally.

<a id="ethpwn.ethlib.contract_registry.ContractRegistry.register_contract_metadata"></a>

#### register\_contract\_metadata

```python
def register_contract_metadata(metadata: 'ContractMetadata',
                               address=None,
                               deploy_tx_hash=None,
                               deploy_tx_receipt: TxReceipt = None,
                               deploy_wallet=None)
```

Add information about a deployed contract to the registry. If the contract is already registered, it is
updated / merged with the new information.

If a contract is newly registered, the registry is automatically saved back to disk.

<a id="ethpwn.ethlib.contract_registry.ContractRegistry.__contains__"></a>

#### \_\_contains\_\_

```python
def __contains__(contract_address) -> bool
```

Check if the given contract address has registered metadata available in the registry.

**Arguments**:

- `contract_address`: The address of the contract

<a id="ethpwn.ethlib.contract_registry.ContractRegistry.__getitem__"></a>

#### \_\_getitem\_\_

```python
def __getitem__(contract_address) -> ContractInstance
```

Get the registered metadata for the given contract address (if any). Throws an exception if no metadata is
registered for the given contract address.

<a id="ethpwn.ethlib.contract_registry.ContractRegistry.get"></a>

#### get

```python
def get(contract_address, default=None) -> ContractInstance
```

Get the registered metadata for the given contract address (if any). Returns the given default value if no
metadata is registered for the given contract address.

<a id="ethpwn.ethlib.contract_registry.ContractRegistry.store"></a>

#### store

```python
def store(contract_registry_dir)
```

Store the registry to the given directory. Creates the directory if it does not exist.
Stores each contract metadata to `contract_registry_dir/<address>.json`.

<a id="ethpwn.ethlib.contract_registry.ContractRegistry.load"></a>

#### load

```python
@staticmethod
def load(contract_registry_dir) -> 'ContractRegistry'
```

Load the registry from the given directory. Loads each contract metadata from `contract_registry_dir/<address>.json`.

<a id="ethpwn.ethlib.contract_registry.contract_registry"></a>

#### contract\_registry

```python
def contract_registry() -> ContractRegistry
```

Get the global contract registry. Loads the registry from disk if it is not already loaded.

<a id="ethpwn.ethlib.contract_registry.load_or_create_contract_registry"></a>

#### load\_or\_create\_contract\_registry

```python
def load_or_create_contract_registry() -> ContractRegistry
```

Load the contract registry from disk if it exists, or create a new one if it does not exist.

<a id="ethpwn.ethlib.contract_registry.register_deployed_contract"></a>

#### register\_deployed\_contract

```python
def register_deployed_contract(metadata,
                               address=None,
                               deploy_tx_hash=None,
                               deploy_tx_receipt: TxReceipt = None)
```

Helper function to easily register a deployed contract. If the contract is already registered, it is
updated / merged with the new information.

<a id="ethpwn.ethlib.contract_registry.register_contract_at_address"></a>

#### register\_contract\_at\_address

```python
def register_contract_at_address(metadata, address)
```

Helper function to easily register a contract at a given address. If the contract is already registered, it is
updated / merged with the new information.

<a id="ethpwn.ethlib.contract_registry.decode_function_input"></a>

#### decode\_function\_input

```python
def decode_function_input(contract_address, input, guess=False)
```

Decode the given function input for the given contract address. If the contract is registered in the contract
registry, the correct metadata is used to decode the input. Otherwise, if `guess=True`, the input is decoded using the metadata
of all known contracts, and the best guess is returned.

