# Table of Contents

* [ethpwn.ethlib.transactions](#ethpwn.ethlib.transactions)
  * [InsufficientFundsError](#ethpwn.ethlib.transactions.InsufficientFundsError)
  * [TransactionFailedError](#ethpwn.ethlib.transactions.TransactionFailedError)
  * [encode\_transaction](#ethpwn.ethlib.transactions.encode_transaction)
  * [transfer\_funds](#ethpwn.ethlib.transactions.transfer_funds)
  * [debug\_transaction](#ethpwn.ethlib.transactions.debug_transaction)
  * [transact](#ethpwn.ethlib.transactions.transact)
  * [deploy\_bare\_contract](#ethpwn.ethlib.transactions.deploy_bare_contract)
  * [deploy\_shellcode\_contract](#ethpwn.ethlib.transactions.deploy_shellcode_contract)

<a id="ethpwn.ethlib.transactions"></a>

# ethpwn.ethlib.transactions

<a id="ethpwn.ethlib.transactions.InsufficientFundsError"></a>

## InsufficientFundsError Objects

```python
class InsufficientFundsError(Exception)
```

An exception that is raised when a transaction fails due to insufficient funds.

<a id="ethpwn.ethlib.transactions.TransactionFailedError"></a>

## TransactionFailedError Objects

```python
class TransactionFailedError(Exception)
```

An exception that is raised when a transaction fails. This is usually due to an uncaught revert or violated assert
in the contract.

<a id="ethpwn.ethlib.transactions.encode_transaction"></a>

#### encode\_transaction

```python
def encode_transaction(contract_function=None, from_addr=None, **kwargs)
```

Encode a transaction to call a `contract_function` or a raw transaction if `contract_function` is None.

<a id="ethpwn.ethlib.transactions.transfer_funds"></a>

#### transfer\_funds

```python
def transfer_funds(from_addr, to_addr, value=None, **kwargs)
```

Transfer funds from `from_addr` to `to_addr`. If `value` is None, transfer all available funds minus the transaction cost.

<a id="ethpwn.ethlib.transactions.debug_transaction"></a>

#### debug\_transaction

```python
def debug_transaction(tx_hash, txdata)
```

Simulate a transaction and attempt to debug the state using `ipdb` if it fails.

TODO: we would like this to automatically set up `ethdbg` to debug the transaction failure if requested.

<a id="ethpwn.ethlib.transactions.transact"></a>

#### transact

```python
def transact(contract_function=None,
             private_key=None,
             force=False,
             wait_for_receipt=True,
             from_addr=None,
             **tx) -> (HexBytes, TxReceipt)
```

Send a transaction to the blockchain. If `contract_function` is not None, call the contract function.

If `private_key` is None, use the default signing key from the global context.
If `from_addr` is None, use the default from address from the global context.
If `wait_for_receipt` is True, wait for the transaction receipt and return it.
If `force` is True, ignore simulated errors and push the transaction to the blockchain depite the likely revert.

<a id="ethpwn.ethlib.transactions.deploy_bare_contract"></a>

#### deploy\_bare\_contract

```python
def deploy_bare_contract(bin, metadata=None, **tx_kwargs)
```

Deploy a contract with the given constructor bytecode. If `metadata` is not None, use the ABI from the metadata to create a
contract object.

<a id="ethpwn.ethlib.transactions.deploy_shellcode_contract"></a>

#### deploy\_shellcode\_contract

```python
def deploy_shellcode_contract(shellcode, **tx_kwargs)
```

Deploy a contract with the given shellcode. This will create a shellcode deployer constructor that will deploy the given shellcode
when called.

