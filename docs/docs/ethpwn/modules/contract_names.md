<a id="ethpwn.ethlib.contract_names"></a>

# ethpwn.ethlib.contract\_names

<a id="ethpwn.ethlib.contract_names.ContractNames"></a>

## ContractNames Objects

```python
class ContractNames()
```

AMaps contract addresses to contract names.
Serialized to the local configuration directory to ensure persistence across runs. This allows us to remember
all contracts we've referred to by name in the past.

In the future we plan on having a global name registry shared across all users of ethpwn that users can opt into.

<a id="ethpwn.ethlib.contract_names.ContractNames.register_contract_name"></a>

#### register\_contract\_name

```python
def register_contract_name(contract_address, contract_name)
```

Name the given contract address with the given contract name.

<a id="ethpwn.ethlib.contract_names.ContractNames.get_contract_names"></a>

#### get\_contract\_names

```python
def get_contract_names(contract_address) -> List[str]
```

Get the names registered for a given contract address.

<a id="ethpwn.ethlib.contract_names.ContractNames.get_contract_address"></a>

#### get\_contract\_address

```python
def get_contract_address(contract_name) -> str
```

Get the address of the given contract name.

<a id="ethpwn.ethlib.contract_names.ContractNames.store"></a>

#### store

```python
def store(contract_names_path)
```

Store the names to the given JSON file.

<a id="ethpwn.ethlib.contract_names.ContractNames.load"></a>

#### load

```python
@staticmethod
def load(contract_names_path) -> 'ContractNames'
```

Load the names from the given JSON path.

<a id="ethpwn.ethlib.contract_names.contract_names"></a>

#### contract\_names

```python
def contract_names() -> ContractNames
```

Get the global contract names. Loads the registry from disk if it is not already loaded.

<a id="ethpwn.ethlib.contract_names.load_or_create_contract_names"></a>

#### load\_or\_create\_contract\_names

```python
def load_or_create_contract_names() -> ContractNames
```

Load the contract names from disk, or create a new one if it does not exist.

<a id="ethpwn.ethlib.contract_names.register_contract_name"></a>

#### register\_contract\_name

```python
def register_contract_name(address, name)
```

Helper function to easily register a contract at a given address. If the contract is already registered, it is
updated / merged with the new information.

<a id="ethpwn.ethlib.contract_names.contract_by_name"></a>

#### contract\_by\_name

```python
def contract_by_name(name)
```

Helper function to easily get the address of a contract by name.

<a id="ethpwn.ethlib.contract_names.names_for_contract"></a>

#### names\_for\_contract

```python
def names_for_contract(address)
```

Helper function to easily get the names of a contract by address.

<a id="ethpwn.ethlib.contract_names.name_for_contract"></a>

#### name\_for\_contract

```python
def name_for_contract(address)
```

Helper function to easily get a name of a contract by address.

