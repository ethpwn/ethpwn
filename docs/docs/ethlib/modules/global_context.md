# Table of Contents

* [ethtools.pwn.global\_context](#ethtools.pwn.global_context)
  * [Web3Context](#ethtools.pwn.global_context.Web3Context)
    * [try\_auto\_connect](#ethtools.pwn.global_context.Web3Context.try_auto_connect)
    * [default\_from\_addr](#ethtools.pwn.global_context.Web3Context.default_from_addr)
    * [default\_signing\_key](#ethtools.pwn.global_context.Web3Context.default_signing_key)
    * [log\_level](#ethtools.pwn.global_context.Web3Context.log_level)
    * [connect](#ethtools.pwn.global_context.Web3Context.connect)
    * [connect\_http](#ethtools.pwn.global_context.Web3Context.connect_http)
    * [connect\_ipc](#ethtools.pwn.global_context.Web3Context.connect_ipc)
    * [connect\_websocket](#ethtools.pwn.global_context.Web3Context.connect_websocket)
    * [pessimistic\_gas\_price\_estimate](#ethtools.pwn.global_context.Web3Context.pessimistic_gas_price_estimate)
    * [pessimistic\_transaction\_cost](#ethtools.pwn.global_context.Web3Context.pessimistic_transaction_cost)
  * [with\_local\_context](#ethtools.pwn.global_context.with_local_context)

<a id="ethtools.pwn.global_context"></a>

# ethtools.pwn.global\_context

Global context accessible from anywhere in the ethpwn package.

<a id="ethtools.pwn.global_context.Web3Context"></a>

## Web3Context Objects

```python
class Web3Context()
```

A context holding global state used by ethpwn.

<a id="ethtools.pwn.global_context.Web3Context.try_auto_connect"></a>

#### try\_auto\_connect

```python
def try_auto_connect()
```

Try to auto connect to a node if the default network is set and autoconnect is not disabled.

<a id="ethtools.pwn.global_context.Web3Context.default_from_addr"></a>

#### default\_from\_addr

```python
@property
def default_from_addr()
```

Get the default from address as set or via the default wallet

<a id="ethtools.pwn.global_context.Web3Context.default_signing_key"></a>

#### default\_signing\_key

```python
@property
def default_signing_key()
```

Get the default signing key

<a id="ethtools.pwn.global_context.Web3Context.log_level"></a>

#### log\_level

```python
@property
def log_level()
```

Get the log level of the logger

<a id="ethtools.pwn.global_context.Web3Context.connect"></a>

#### connect

```python
def connect(url, can_fail=False, **kwargs)
```

Connect to the Ethereum node at `url` via HTTP/HTTPS, Websocket, or IPC depending on the URL scheme.
If `can_fail` is True, then the function will return False if it fails to connect instead of raising an exception.

<a id="ethtools.pwn.global_context.Web3Context.connect_http"></a>

#### connect\_http

```python
def connect_http(url, can_fail=False, **kwargs)
```

Connect to a remote Ethereum node via HTTP/HTTPS

<a id="ethtools.pwn.global_context.Web3Context.connect_ipc"></a>

#### connect\_ipc

```python
def connect_ipc(path='/home/eth/.ethereum/geth.ipc', can_fail=False)
```

Connect to a local Ethereum node via IPC

<a id="ethtools.pwn.global_context.Web3Context.connect_websocket"></a>

#### connect\_websocket

```python
def connect_websocket(url, can_fail=False, **kwargs)
```

Connect to an Ethereum node via WebSockets

<a id="ethtools.pwn.global_context.Web3Context.pessimistic_gas_price_estimate"></a>

#### pessimistic\_gas\_price\_estimate

```python
def pessimistic_gas_price_estimate()
```

Estimate the gas price for a transaction. This is a pessimistic estimate that will
overestimate the gas price by a factor of 2. This should be good enough to mostly
ensure that the transaction will be mined in a reasonable amount of time.

<a id="ethtools.pwn.global_context.Web3Context.pessimistic_transaction_cost"></a>

#### pessimistic\_transaction\_cost

```python
def pessimistic_transaction_cost(gas_used_estimate)
```

Estimate the cost of a transaction. This is a pessimistic estimate that will
overestimate the gas price by a factor of 2. This should be good enough to mostly
ensure that the transaction will be mined in a reasonable amount of time.

<a id="ethtools.pwn.global_context.with_local_context"></a>

#### with\_local\_context

```python
@contextlib.contextmanager
def with_local_context(**kwargs)
```

Temporarily set the global context to a new context. Will restore the old context when the
context manager exits.

