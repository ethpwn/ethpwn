<a id="ethpwn.ethlib.contract_labels"></a>

# ethpwn.ethlib.contract\_labels

<a id="ethpwn.ethlib.contract_labels.ContractLabels"></a>

## ContractLabels Objects

```python
class ContractLabels()
```

Maps contract addresses to contract labels.
Serialized to the local configuration directory to ensure persistence across runs. This allows us to remember
all contracts we've referred to by a label in the past.

<a id="ethpwn.ethlib.contract_labels.ContractLabels.register_contract_label"></a>

#### register\_contract\_label

```python
def register_contract_label(contract_address, contract_label)
```

Assign the given contract address to a label.

<a id="ethpwn.ethlib.contract_labels.ContractLabels.get_contract_labels"></a>

#### get\_contract\_labels

```python
def get_contract_labels(contract_address) -> List[str]
```

Get the labels registered for a given contract address.

<a id="ethpwn.ethlib.contract_labels.ContractLabels.get_contract_address"></a>

#### get\_contract\_address

```python
def get_contract_address(label) -> str
```

Get the address of the given contract label.

<a id="ethpwn.ethlib.contract_labels.ContractLabels.store"></a>

#### store

```python
def store(contract_labels_path)
```

Store the labels to the given JSON file.

<a id="ethpwn.ethlib.contract_labels.ContractLabels.load"></a>

#### load

```python
@staticmethod
def load(contract_labels_path) -> 'ContractLabels'
```

Load the labels from the given JSON path.

<a id="ethpwn.ethlib.contract_labels.contract_labels"></a>

#### contract\_labels

```python
def contract_labels() -> ContractLabels
```

Get the global contract labels. Loads the registry from disk if it is not already loaded.

<a id="ethpwn.ethlib.contract_labels.load_or_create_contract_labels"></a>

#### load\_or\_create\_contract\_labels

```python
def load_or_create_contract_labels() -> ContractLabels
```

Load the contract labels from disk, or create a new one if it does not exist.

<a id="ethpwn.ethlib.contract_labels.register_contract_label"></a>

#### register\_contract\_label

```python
def register_contract_label(address, label)
```

Helper function to easily register a contract at a given address. If the contract is already registered, it is
updated / merged with the new information.

<a id="ethpwn.ethlib.contract_labels.contract_by_label"></a>

#### contract\_by\_label

```python
def contract_by_label(label)
```

Helper function to easily get the address of a contract by label.

<a id="ethpwn.ethlib.contract_labels.labels_for_contract"></a>

#### labels\_for\_contract

```python
def labels_for_contract(address)
```

Helper function to easily get the labels of a contract by address.

<a id="ethpwn.ethlib.contract_labels.label_for_contract"></a>

#### label\_for\_contract

```python
def label_for_contract(address)
```

Helper function to easily get a label of a contract by address.

