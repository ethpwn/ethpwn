<a id="ethtools.pwn.currency_utils"></a>

# ethtools.pwn.currency\_utils

Utilities for dealing with the different units of currency in the Ethereum ecosystem.

<a id="ethtools.pwn.currency_utils.parse_wei"></a>

#### parse\_wei

```python
def parse_wei(value_string)
```

Parse a string representing into a wei value. The string can be in ether, gwei, or wei.
If no unit is specified, it is assumed to be wei.

<a id="ethtools.pwn.currency_utils.wei"></a>

#### wei

```python
def wei(ether=None, gwei=None, wei=None)
```

Convert some amount of ether, gwei, and/or wei to wei. Returns the sum of all values so you can
do `wei(ether=1, gwei=1)` to get 1 ether and 1 gwei in wei.

<a id="ethtools.pwn.currency_utils.ether"></a>

#### ether

```python
def ether(wei)
```

Convert wei to ether

<a id="ethtools.pwn.currency_utils.gwei"></a>

#### gwei

```python
def gwei(wei)
```

Convert wei to gwei