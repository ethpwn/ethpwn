<a id="ethtools.pwn.global_context"></a>

# ethtools.pwn.global\_context

Global context accessible from anywhere in the ethpwn package (similar to the `context` in `pwntools`).

<a id="ethtools.pwn.global_context.Web3Context"></a>

## Web3Context Class

```python
class Web3Context()
```

<a id="ethtools.pwn.global_context.Web3Context.default_from_addr"></a>

#### default\_from\_addr

```python
@property
def default_from_addr()
```

Get the default "from" address as set, or via the default wallet.

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

Connect to an Ethereum node via HTTP/HTTPS, Websocket, or IPC depending on the URL scheme.
If `can_fail` is True, the method will return `False` if cannot connect, otherwise, will raise an Exception.

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