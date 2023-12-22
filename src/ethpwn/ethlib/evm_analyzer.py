

from .global_context import context

from .evm.analyzer import EVMAnalyzer

def get_evm_at_block(block_number:int, **kwargs) -> EVMAnalyzer:
    '''
    Return an EVMAnalyzer instance for the given block number.
    '''
    return EVMAnalyzer.from_block_number(context.w3, block_number)


def get_evm_at_txn(txn:str) -> EVMAnalyzer:
    '''
    Return an EVMAnalyzer instance for the given transaction hash.
    '''
    w3txn = context.w3.eth.get_transaction(txn)
    block_number = w3txn['blockNumber']
    w3block = context.w3.eth.get_block(block_number)

    a = EVMAnalyzer.from_block_number(context.w3, block_number)

    #print(f"Applying transactions up to {txn}")

    # apply the transactions up to the one we want 
    for t in w3block.transactions:
        if t.hex() == txn:
            break
        else:   
            _, receipt, comp = a.next_transaction()
    
    return a