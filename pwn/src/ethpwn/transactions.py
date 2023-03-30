from .assembly_utils import create_shellcode_deployer_bin
from .currency_utils import ether
from .global_context import context
import web3
from hexbytes import HexBytes
from web3.types import TxReceipt
from web3.datastructures import AttributeDict

class InsufficientFundsError(Exception):
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
    def __init__(self, tx_hash, tx_receipt) -> None:
        self.tx_hash = tx_hash
        self.tx_receipt = tx_receipt
        super().__init__()

    def __str__(self) -> str:
        return f"Transaction {self.tx_hash} failed with status {self.tx_receipt['status']}: {self.tx_receipt}"

    def __repr__(self) -> str:
        return f"TransactionFailedError({self.tx_hash}, {self.tx_receipt})"

def encode_transaction(contract_function=None, from_addr=None, **kwargs):
    if from_addr is None:
        from_addr = context.default_from_addr
    assert from_addr is not None
    extra = kwargs.copy()
    extra['nonce'] = kwargs.get('nonce', context.w3.eth.get_transaction_count(from_addr))
    extra['from'] = from_addr
    # extra['maxPriorityFeePerGas'] = kwargs.get('maxPriorityFeePerGas', 1_000 * (10 ** 9)) # 1k gwei -- a lot (tip the miner for priority)
    # extra['maxFeePerGas'] = kwargs.get('maxFeePerGas', 1_000 * (10 ** 9)) # 1k gwei -- a lot
    extra['value'] = kwargs.get('value', 0)
    extra['gas'] = kwargs.get('gas', 0)
    if contract_function is not None and type(contract_function):
        tx = contract_function.build_transaction(extra)
    else:
        tx = extra
    return tx

def transfer_funds(from_addr, to_addr, value=None, **kwargs):
    if 'gasPrice' not in kwargs:
        kwargs['gasPrice'] = context.pessimistic_gas_price_estimate()

    if value is None:
        balance = int(context.w3.eth.get_balance(from_addr) * 0.98)
        tx = encode_transaction(to=to_addr, value=balance, from_addr=from_addr, **kwargs)
        estimated_gas = context.w3.eth.estimate_gas(tx)
        max_transferable_value = balance - context.pessimistic_transaction_cost(estimated_gas)

        value = max_transferable_value

    context.logger.info(f"Transferring {context.w3.from_wei(value, 'ether')} ether from {from_addr} to {to_addr}")

    return transact(to=to_addr, value=value, from_addr=from_addr, **kwargs)

def debug_transaction(tx_hash, txdata):
    try:
        context.w3.eth.call(txdata)
    except Exception as e:
        print(e)
        import ipdb; ipdb.set_trace()
        raise e

def transact(contract_function=None, private_key=None, force=False, wait_for_receipt=True, from_addr=None, **tx) -> (HexBytes, TxReceipt):
    if private_key is None:
        private_key = context.default_signing_key
    assert private_key is not None

    tx = encode_transaction(contract_function, from_addr=from_addr, **tx)
    from_addr = tx['from']

    if 'gas' not in tx or tx['gas'] == 0:
        try:
            gas = context.w3.eth.estimate_gas(tx)
            tx.update({'gas': gas * 2})
        except:
            if force:
                context.logger.warn(f"Failed to estimate gas, using 2 million instead (forced, continuing anyway)")
                tx['gas'] = 2000000
            else:
                raise


    balance = context.w3.eth.get_balance(from_addr)
    funds_required = tx['value'] + tx['gas'] * 2 * tx['gasPrice']
    if funds_required >= balance:
        err_msg = f"Likely insufficient funds to send transaction {contract_function}: {balance=} < {tx['value']=} + {tx['gas']=} * 4"
        if force:
            context.logger.error(err_msg + " (forced, continuing anyway)")
        else:
            raise InsufficientFundsError(funds_required, balance, err_msg)

    tx_signed = context.w3.eth.account.sign_transaction(tx, private_key=private_key)
    transaction_hash = context.w3.eth.send_raw_transaction(tx_signed.rawTransaction)
    context.logger.info(f"Sent transaction {contract_function}: {context.w3.to_hex(transaction_hash)}: {from_addr} -> {tx['to']} ({ether(tx['value'])} ether)")

    if wait_for_receipt:
        tx_receipt = context.w3.eth.wait_for_transaction_receipt(context.w3.to_hex(tx_signed.hash), timeout=120)
        context.logger.info(f"Received receipt (block_number={tx_receipt['blockNumber']})")
        if tx_receipt['status'] != 1:
            debug_transaction(transaction_hash, tx)
            raise TransactionFailedError(context.w3.to_hex(tx_signed.hash), tx_receipt)
        return transaction_hash, tx_receipt
    else:
        return transaction_hash

def deploy_bare_contract(bin, metadata=None, **tx_kwargs):
    if metadata is None:
        abi = {}
    else:
        abi = metadata.abi


    if 'gasPrice' not in tx_kwargs:
        tx_kwargs['gasPrice'] = context.pessimistic_gas_price_estimate()

    tx_hash, tx_receipt = transact(to='', data=HexBytes(bin).hex(), **tx_kwargs)
    print(tx_receipt)
    return tx_hash, tx_receipt, context.w3.eth.contract(tx_receipt['contractAddress'])

def deploy_shellcode_contract(shellcode, **tx_kwargs):
    return deploy_bare_contract(create_shellcode_deployer_bin(shellcode), **tx_kwargs)