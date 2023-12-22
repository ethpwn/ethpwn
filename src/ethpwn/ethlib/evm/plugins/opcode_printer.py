
import typing
from .base import *

class JustPrintOpcode(BaseAnalysisPlugin):   
        name = "print_opcode"

        def __init__(self):
            super().__init__()
    
        def pre_opcode_hook(self, opcode, computation):
            print(opcode.mnemonic)