import time
from .utils import normalize_contract_address, run_in_new_terminal
from .assembly_utils import create_shellcode_deployer_bin
from .currency_utils import ether, wei
from .global_context import context
import web3
from hexbytes import HexBytes
from web3.types import TxReceipt
from web3.datastructures import AttributeDict

class InsufficientFundsError(Exception):
    '''
    An exception that is raised when a transaction fails due to insufficient funds.
    '''
    def __init__(self, required_balance, actual_balance, cause) -> None:
        self.required_balance = required_balance
        self.actual_balance = actual_balance
        self.cause = cause
        super().__init__()

    def __str__(self) -> str:
        return f"Insufficient funds: {context.w3.from_wei(self.required_balance, 'ether')} ether required, {context.w3.from_wei(self.actual_balance, 'ether')} ether available"

    def __repr__(self) -> str:
        return f"InsufficientFundsError({self.required_balance}, {self.actual_balance}, {self.cause})"

class TransactionFailedError(Exception):
    '''
    An exception that is raised when a transaction fails. This is usually due to an uncaught revert or violated assert
    in the contract.
    '''
    def __init__(self, tx_hash, tx_receipt) -> None:
        self.tx_hash = tx_hash
        self.tx_receipt = tx_receipt
        super().__init__()

    def __str__(self) -> str:
        return f"Transaction {self.tx_hash} failed with status {self.tx_receipt['status']}: {self.tx_receipt}"

    def __repr__(self) -> str:
        return f"TransactionFailedError({self.tx_hash}, {self.tx_receipt})"

def encode_transaction(contract_function=None, from_addr=None, **kwargs):
    '''
    Encode a transaction to call a `contract_function` or a raw transaction if `contract_function` is None.
    '''
    if from_addr is None:
        from_addr = context.default_from_addr
    assert from_addr is not None
    extra = kwargs.copy()
    extra['chainId'] = kwargs.get('chainId', context.w3.eth.chain_id)
    extra['nonce'] = kwargs.get('nonce', context.w3.eth.get_transaction_count(from_addr))
    extra['from'] = from_addr
    extra['maxPriorityFeePerGas'] = kwargs.get('maxPriorityFeePerGas', wei(gwei=10)) # 10 gwei -- a lot (tip the miner for priority)
    extra['maxFeePerGas'] = kwargs.get('maxFeePerGas', wei(gwei=1000)) # 1000 gwei -- a lot
    extra['value'] = kwargs.get('value', 0)
    extra['gas'] = kwargs.get('gas', 0)
    if contract_function is not None and type(contract_function):
        tx = contract_function.build_transaction(extra)
    else:
        tx = extra
    return tx

def transfer_funds(from_addr, to_addr, value=None, **kwargs):
    '''
    Transfer funds from `from_addr` to `to_addr`. If `value` is None, transfer all available funds minus the transaction cost.
    '''

    if value is None:
        balance = int(context.w3.eth.get_balance(from_addr) * 0.98)
        tx = encode_transaction(to=to_addr, value=balance, from_addr=from_addr, **kwargs)
        estimated_gas = context.w3.eth.estimate_gas(tx)
        max_transferable_value = balance - context.pessimistic_transaction_cost(estimated_gas)

        value = max_transferable_value

    context.logger.info(f"Transferring {context.w3.from_wei(value, 'ether')} ether from {from_addr} to {to_addr}")

    return transact(to=to_addr, value=value, from_addr=from_addr, **kwargs)

def debug_simulated_transaction(tx):
    '''
    Simulate a transaction and attempt to debug the state using `ipdb` if it fails.
    '''
    to_addr = normalize_contract_address(tx['to'])
    from_addr = normalize_contract_address(tx['from'])
    data = HexBytes(tx['data']).hex()
    run_in_new_terminal([
        '/bin/bash',
        '-c',
        f'ethdbg --target {to_addr} --calldata {data} --sender {from_addr} --value {tx["value"]}; sleep 10'
    ])
    input("Continue? ")

def debug_onchain_transaction(tx_hash):
    '''
    Simulate a transaction and attempt to debug the state using `ipdb` if it fails.

    TODO: we would like this to automatically set up `ethdbg` to debug the transaction failure if requested.
    '''
    run_in_new_terminal([
        '/bin/bash',
        '-c',
        f'ethdbg --txid {HexBytes(tx_hash).hex()}; sleep 10'
    ])
    input("Continue? ")

ERRORS_TO_RETRY = ("nonce too low", "replacement transaction underpriced")

def transact(contract_function=None, private_key=None, force=False, wait_for_receipt=True,
             from_addr=None, retry=3, debug_transaction_errors=None, **tx
            ) -> (HexBytes, TxReceipt):
    '''
    Send a transaction to the blockchain. If `contract_function` is not None, call the contract function.

    If `private_key` is None, use the default signing key from the global context.
    If `from_addr` is None, use the default from address from the global context.
    If `wait_for_receipt` is True, wait for the transaction receipt and return it.
    If `force` is True, ignore simulated errors and push the transaction to the blockchain depite the likely revert.
    '''
    if private_key is None:
        private_key = context.default_signing_key
    assert private_key is not None

    if debug_transaction_errors is None:
        debug_transaction_errors = context.debug_transaction_errors

    tx = encode_transaction(contract_function, from_addr=from_addr, **tx)
    from_addr = tx['from']

    if 'gas' not in tx or tx['gas'] == 0:
        try:
            gas = context.w3.eth.estimate_gas(tx)
            tx.update({'gas': gas * 2})
        except:
            if force:
                context.logger.warn(f"Failed to estimate gas, using 2 million instead (forced, continuing anyway)")
                tx['gas'] = 200000
            else:
                if debug_transaction_errors:
                    debug_simulated_transaction(tx)
                raise


    balance = context.w3.eth.get_balance(from_addr)
    if 'gasPrice' in tx:
        funds_required = tx['value'] + tx['gas'] * 2 * tx['gasPrice']
    else:
        # import ipdb; ipdb.set_trace()
        # max_fee_per_gas = context.w3.eth.max_priority_fee
        funds_required = None
    if funds_required is not None and funds_required >= balance:
        err_msg = f"Likely insufficient funds to send transaction {contract_function}: {balance=} < {tx['value']=} + {tx['gas']=} * 4"
        if force:
            context.logger.error(err_msg + " (forced, continuing anyway)")
        else:
            raise InsufficientFundsError(funds_required, balance, err_msg)

    tx_signed = context.w3.eth.account.sign_transaction(tx, private_key=private_key)
    for i in range(retry):
        try:
            transaction_hash = context.w3.eth.send_raw_transaction(tx_signed.rawTransaction)
            break
        except ValueError as e:
            if e.args[0]['message'] in ERRORS_TO_RETRY:
                context.logger.warn(f"Spurious error {e.args[0]['message']}, blockchain sucks, retrying after 1 second ({i+1}/{retry})")
                time.sleep(1)
                if i != retry - 1:
                    continue
            raise

    context.logger.info(f"Sent transaction {contract_function}: {context.w3.to_hex(transaction_hash)}: {from_addr} -> {tx['to']} ({ether(tx['value'])} ether)")

    if wait_for_receipt:
        tx_receipt = context.w3.eth.wait_for_transaction_receipt(context.w3.to_hex(tx_signed.hash), timeout=120)
        context.logger.info(f"Received receipt (block_number={tx_receipt['blockNumber']})")
        if tx_receipt['status'] != 1 and debug_transaction_errors:
            debug_onchain_transaction(transaction_hash)
            raise TransactionFailedError(context.w3.to_hex(tx_signed.hash), tx_receipt)
        return transaction_hash, tx_receipt
    else:
        return transaction_hash

def deploy_bare_contract(bin, metadata=None, **tx_kwargs):
    '''
    Deploy a contract with the given constructor bytecode. If `metadata` is not None, use the ABI from the metadata to create a
    contract object.
    '''
    if metadata is None:
        abi = []
    else:
        abi = metadata.abi

    tx_hash, tx_receipt = transact(to='', data=HexBytes(bin).hex(), **tx_kwargs)
    print(tx_receipt)
    return tx_hash, tx_receipt, context.w3.eth.contract(tx_receipt['contractAddress'], abi=abi)

def deploy_shellcode_contract(shellcode, **tx_kwargs):
    '''
    Deploy a contract with the given shellcode. This will create a shellcode deployer constructor that will deploy the given shellcode
    when called.
    '''
    return deploy_bare_contract(create_shellcode_deployer_bin(shellcode), **tx_kwargs)