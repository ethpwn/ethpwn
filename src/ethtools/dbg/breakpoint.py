
import re
import hashlib
from .ethdbg_exceptions import InvalidBreakpointException
from .analyzer import ALL_EVM_OPCODES, ComputationAPI, OpcodeAPI

ALLOWED_COND_BPS = ['addr', 'saddr', 'op', 'pc', 'value']
BPS_RE_PATTERN = r'([a-zA-Z]*)(==|!=|<=|>=|>|<|=)(.*)'
ETH_ADDRESS = r'^(0x)?[0-9a-fA-F]{40}$'

class Breakpoint():
    def __init__(self, break_args, temp=False):

        # Processing of the breakpoint conditions
        self.conditions = list()

        self.pc = None
        self.op = None
        self.temp = temp
        self.simple_bp = False

        # signature of the breakpoint to avoid duplicate
        self.signature = None

        # Is this a simple breakpoint?
        # This is the case if len(break_args) == 1 and none of the ALLOWED_COND_BPS is in break_args[0]
        if len(break_args) == 1 and not any(cond_keyword in break_args[0] for cond_keyword in ALLOWED_COND_BPS):
            self.simple_bp = True
            # Is it a valid opcode
            if break_args[0].upper() in ALL_EVM_OPCODES:
                self.op = break_args[0].upper()
                self.signature = hashlib.sha256(str(self.op).encode("utf-8")).hexdigest()
            else:
                # Is it a valid pc?
                try:
                    self.pc = int(break_args[0],16)
                    self.signature = hashlib.sha256(str(self.pc).encode("utf-8")).hexdigest()
                except Exception as e:
                    raise InvalidBreakpointException()
        else:
            for break_arg in break_args:
                break_arg = break_arg.replace(' ', '')
                matches = re.findall(BPS_RE_PATTERN, break_arg)[0]
                if len(matches) != 3:
                    #print(f"Invalid breakpoint condition {break_arg}. Skipping.")
                    continue
                else:
                    what  = matches[0]
                    when  = matches[1]
                    value = matches[2]
                    # Validation of the breakpoints parameters here
                    if self._validate_bp(what, when, value):
                        self.conditions.append((what, when, value))
                        sha256_hash = hashlib.sha256()
                        sha256_hash.update(what.encode('utf-8'))
                        sha256_hash.update(when.encode('utf-8'))
                        sha256_hash.update(value.encode('utf-8'))
                        self.signature = sha256_hash.hexdigest()

                    else:
                        raise InvalidBreakpointException()

    def __str__(self):
        _bp_str = ''

        if self.simple_bp:
            _bp_str += "Simple Breakpoint at "
            if self.op:
                _bp_str += f'{self.op}'
            elif self.pc:
                _bp_str += f'{hex(self.pc)}'
        else:
            _bp_str += "Conditional Breakpoint if "
            for condition in self.conditions:
                what = condition[0]
                when  = condition[1]
                value = condition[2]
                _bp_str += f'{what} {when} {value} '

        return _bp_str

    def _validate_bp(self, what, when, value):
        if what not in ALLOWED_COND_BPS:
            return False

        # Now we want to check the type of the value given a 'what'
        if what == 'pc' or what == 'value':
            try:
                int(value,16)
            except Exception:
                return False
            return True
        elif what == 'op':
            if value.upper() in ALL_EVM_OPCODES:
                return True
            else:
                return False
        elif what == 'addr' or what == 'saddr':
            if re.match(ETH_ADDRESS, value):
                return True
            else:
                return False
        elif 'storage' in what:
            storage_index = what.split('[')[1].split(']')[0]
            try:
                # Storage index must be a hex number
                int(storage_index,16)
            except Exception:
                return False
        else:
            return False

    def eval_bp(self, comp: ComputationAPI, pc: int, opcode: OpcodeAPI, callstack):
        if self.simple_bp:
            if self.op:
                return opcode.mnemonic == self.op
            elif self.pc:
                return self.pc == pc
            else:
                return False
        else:
            for condition in self.conditions:
                what = condition[0]
                when  = condition[1]
                value = condition[2]

                if when == '=':
                    when = '==' # because I'm a nice guy

                if what == 'pc':
                    pc_val = int(value,16)

                    expr = f'{pc_val} {when} {pc}'
                    if not eval(expr):
                        return False

                elif what == 'op':
                    value = value.upper()
                    expr = f'"{value}" {when} "{opcode.mnemonic}"'
                    if not eval(expr):
                        return False

                elif what.strip() in {'addr', 'code_addr', 'code_address', 'code'}:
                    # Warning: this is not checksummed
                    curr_code_addr = '0x' + comp.msg.code_address.hex()
                    value = value.lower()
                    expr = f'"{str(value)}" {when} "{str(curr_code_addr)}"'
                    if not eval(expr):
                        return False

                elif what.strip() in {'saddr', 'storage_addr', 'storage_address'}:
                    # Warning: this is not checksummed
                    curr_storage_addr = '0x' + comp.msg.storage_address.hex()
                    value = value.lower()
                    expr = f'"{str(value)}" {when} "{str(curr_storage_addr)}"'
                    if not eval(expr):
                        return False

                elif what == 'value':
                    msg_val = int(value,16)
                    last_frame = callstack[-1]
                    expr = f'{msg_val} {when} {last_frame.value}'
                    if not eval(expr):
                        return False
                else:
                    return False

            # It's a hit of a conditional bp!
            return True