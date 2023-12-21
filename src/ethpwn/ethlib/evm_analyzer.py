

from .global_context import context

from .evm.analyzer import EVMAnalyzer

def get_evm_at_block(block_number:int, **kwargs) -> EVMAnalyzer:
    '''
    Return an EVMAnalyzer instance for the given block number.
    '''
    return EVMAnalyzer.from_block_number(context.w3, block_number)

def get_evm_at_block_and_tx_index(block_number:int, txindex:int, **kwargs) -> EVMAnalyzer:
    '''
    Return an EVMAnalyzer instance for the given block number and transaction index.
    '''
    import ipdb; ipdb.set_trace()
    return EVMAnalyzer.from_block_and_txindex(context.w3, block_number, txindex)