<a id="ethpwn.ethlib.utils"></a>

# ethpwn.ethlib.utils

<a id="ethpwn.ethlib.utils.normalize_contract_address"></a>

#### normalize\_contract\_address

```python
@functools.lru_cache(maxsize=1024)
def normalize_contract_address(address) -> str
```

Normalize a contract address. This ensures all addresses are checksummed and have the 0x prefix.

<a id="ethpwn.ethlib.utils.get_shared_prefix_len"></a>

#### get\_shared\_prefix\_len

```python
def get_shared_prefix_len(a, b)
```

Get the length of the shared prefix of two strings.

<a id="ethpwn.ethlib.utils.to_snake_case"></a>

#### to\_snake\_case

```python
def to_snake_case(s: str) -> str
```

Convert a string to snake case.

<a id="ethpwn.ethlib.utils.show_diff"></a>

#### show\_diff

```python
def show_diff(a, b, show_old_new=False)
```

Show a nice `rich` table of the diff between two objects using `deepdiff`.

<a id="ethpwn.ethlib.utils.get_chainid"></a>

#### get\_chainid

```python
def get_chainid(chain_name)
```

Get the chain id for a given chain name.

<a id="ethpwn.ethlib.utils.get_chain_name"></a>

#### get\_chain\_name

```python
def get_chain_name(id)
```

Get the chain name for a given chain id.

