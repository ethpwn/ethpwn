from contextlib import contextmanager
from .transactions import transact
from .global_context import context

@contextmanager
def destroy_context_manager(result, destroy_function, **kwargs):
    tx_hash, tx_receipt = result
    yield (tx_receipt, tx_hash)
    transact(destroy_function, tx_hash=tx_hash)