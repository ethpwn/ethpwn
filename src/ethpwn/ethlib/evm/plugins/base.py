
from eth.vm.base import VM
from eth.rlp.transactions import SignedTransactionMethods
from eth.vm.opcode import Opcode
from eth.abc import (BlockHeaderAPI, ComputationAPI, MessageAPI, OpcodeAPI,
                     ReceiptAPI)

from .utils import *
from ..analyzer import EVMAnalyzer


class BaseAnalysisPlugin:
    PRE_TRANSACTION_PRIORITY: int = 100
    POST_TRANSACTION_PRIORITY: int = 100
    PRE_OPERATION_PRIORITY: int = 100
    POST_OPERATION_PRIORITY: int = 100
    EXCEPTION_PRIORITY: int = 100
    name = ''

    def __init__(self, **kwargs) -> None:
        return
    
    def install_on(self, analyzer: EVMAnalyzer):
        analyzer.register_pre_txn_setup(self.PRE_TRANSACTION_PRIORITY, self.pre_transaction_hook)
        analyzer.register_post_txn_setup(self.POST_TRANSACTION_PRIORITY, self.post_transaction_hook)
        analyzer.register_pre_opcode_hook(self.PRE_OPERATION_PRIORITY, self.pre_opcode_hook)
        analyzer.register_post_opcode_hook(self.POST_OPERATION_PRIORITY, self.post_opcode_hook)
        analyzer.register_opcode_exception_hook(self.EXCEPTION_PRIORITY, self.opcode_exception_hook)

    def pre_transaction_hook(self, vm: VM, txn: SignedTransactionMethods):
        pass

    def post_transaction_hook(self, vm: VM, receipt: ReceiptAPI, computation: ComputationAPI):
        pass

    def pre_opcode_hook(self, opcode: Opcode, computation: ComputationAPI):
        pass

    def post_opcode_hook(self, opcode: Opcode, computation: ComputationAPI):
        pass

    def opcode_exception_hook(self, opcode: Opcode, computation: ComputationAPI, e: Exception):
        pass