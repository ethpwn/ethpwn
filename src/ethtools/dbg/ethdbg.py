#!/usr/bin/env python3

import argparse
import functools
import os
import re
import sys
import cmd
import traceback
import sha3
import string

from hexdump import hexdump
from typing import List
from alive_progress import alive_bar

from hexbytes import HexBytes
from web3.datastructures import AttributeDict
from pyevmasm import disassemble_one, Instruction

import rich
from rich import print as rich_print
from rich.table import Table
from rich.tree import Tree

from ..pwn.prelude import *
from ..pwn.utils import normalize_contract_address
from ..pwn.config.wallets import get_wallet

from .breakpoint import Breakpoint, ETH_ADDRESS
from .analyzer import Analyzer

from .transaction_debug_target import TransactionDebugTarget
from .analyzer import *
from .utils import *
from .ethdbg_exceptions import ExitCmdException, InvalidBreakpointException, RestartDbgException, InvalidTargetException

from eth_utils.curried import to_canonical_address

def get_w3_provider(web3_host):
    if web3_host.startswith('http'):
        context.connect_http(
            web3_host
        )
    elif web3_host.startswith('ws'):
        context.connect_websocket(
            web3_host,
            websocket_timeout=60 * 5,
            websocket_kwargs={
                'max_size': 1024 * 1024 * 1024,
            },
        )
    else:
        raise Exception("Unknown web3 provider")

    w3 = context.w3
    assert w3.is_connected()
    return w3

FETCHED_VERIFIED_CONTRACTS = set()

def get_source_code(debug_target: TransactionDebugTarget, contract_address: HexBytes, pc: int):
    global FETCHED_VERIFIED_CONTRACTS
    contract_address = normalize_contract_address(contract_address)
    registry = contract_registry()

    if contract_address not in FETCHED_VERIFIED_CONTRACTS and registry.get(contract_address) is None:
        import ipdb; ipdb.set_trace()
        # try to fetch the verified contract
        try:
            fetch_verified_source_code(contract_address, None) # auto-detect etherscan api key and fetch the code
        except Exception as ex:
            # print traceback
            traceback.print_exc()
            print(f"Failed to fetch verified source code for {contract_address}: {ex}")
        FETCHED_VERIFIED_CONTRACTS.add(contract_address)

    contract = registry.get(contract_address)

    if contract is None:
        return None

    if debug_target.target_address is None or int.from_bytes(HexBytes(debug_target.target_address), byteorder='big') == 0:
        closest_instruction_idx = contract.metadata.closest_instruction_index_for_constructor_pc(pc, fork=debug_target.fork)
        source_info = contract.metadata.source_info_for_constructor_instruction_idx(closest_instruction_idx)
    else:
        closest_instruction_idx = contract.metadata.closest_instruction_index_for_runtime_pc(pc, fork=debug_target.fork)
        source_info = contract.metadata.source_info_for_runtime_instruction_idx(closest_instruction_idx)
    if source_info is None:
        return None
    return source_info.pretty_print_source(context_lines=1)


def read_storage_typed_value(read_storage, storage_layout, storage_value):

    storage_type = storage_layout['types'][storage_value['type']]

    # read_storage = function taking a slot and returning a value
    if storage_type['encoding'] == 'inplace':
        if int(storage_type['numberOfBytes']) > 32:
            import ipdb; ipdb.set_trace()
            # assert False, "Don't know how to handle this yet"
            return "<UNSUPPORTED STORAGE TYPE>"
        value = read_storage(int(storage_value['slot']))
        # lower-order-alignment means it's easier to flip it, index, flip it back
        value = value[::-1]
        value = value[int(storage_value['offset']):int(storage_value['offset']) + int(storage_type['numberOfBytes'])]
        value = value[::-1]
        # TODO format it out of the bytes based on the label?
        if storage_type['label'].split()[0] == 'address' or storage_type['label'].split()[0] == 'contract':
            # so far seen: "address", "address payable", "contract <name>"
            return HexBytes(value).hex()
        elif re.fullmatch('uint[0-9]+', storage_type['label']):
            num_bits = int(storage_type['label'][4:])
            assert num_bits % 8 == 0
            num_bytes = num_bits // 8
            assert len(value) == num_bytes
            assert storage_type['numberOfBytes'] == str(num_bytes)
            return int.from_bytes(value, byteorder='big')
        elif storage_type['label'] == 'bool':
            assert len(value) == 1
            assert storage_type['numberOfBytes'] == '1'
            return int.from_bytes(value, byteorder='big') != 0
        elif storage_type['label'] == 'bytes32':
            assert len(value) == 32
            assert storage_type['numberOfBytes'] == '32'
            return value
        else:
            import ipdb; ipdb.set_trace()
            # assert False, "Don't know how to handle this yet"
            return "<UNSUPPORTED STORAGE TYPE>"
        return HexBytes(value)

    elif storage_type['encoding'] == 'mapping':

        # TODO implement and print this:
        '''
        The value corresponding to a mapping key k is located at keccak256(h(k) . p) where . is concatenation and h is a function that is applied to the key depending on its type:

        for value types, h pads the value to 32 bytes in the same way as when storing the value in memory.

        for strings and byte arrays, h(k) is just the unpadded data.

        '''
        slot = int(storage_value['slot'])
        return None

    elif storage_type['encoding'] == 'dynamic_array':
        num_elements = read_storage(int(storage_value['slot']))
        num_elements = int.from_bytes(num_elements, byteorder='big')
        element_type = storage_layout['types'][storage_type['base']]
        element_size = int(element_type['numberOfBytes'])
        num_slots = (num_elements * element_size + 31) // 32
        slot_start = int.from_bytes(keccak(int.to_bytes(int(storage_value['slot']), 32, byteorder='big')), byteorder='big')
        # TODO: Lukas: decode nicer
        slots = [HexBytes(read_storage(slot_start + i))[-element_size:] for i in range(num_slots)]
        return {
            'data_start_slot': slot_start,
            'num_elements': num_elements,
            'element_type': element_type,
            'slots': slots,
        }

    elif storage_type['encoding'] == 'bytes':
        slot = read_storage(int(storage_value['slot']))

        if slot[-1] & 1 == 0:
            length = slot[-1] // 2
            assert length <= 31
            data_read = HexBytes(slot[:length]) # inplace bytes, less than 32 bytes in length
        else:
            length = int.from_bytes(slot, byteorder='big') // 2
            num_slots = (length + 31) // 32
            slots = [read_storage(int(storage_value['slot']) + i) for i in range(num_slots)]
            data_read = HexBytes(b''.join(slots))
        if storage_type['label'] == 'string':
            data_read = data_read.decode('utf-8')
        else:
            assert storage_type['label'] == 'bytes'
        return data_read

    else:
        raise Exception(f'Unknown storage encoding {storage_type["encoding"]}')


def _get_storage_layout_table_for(read_storage, title, storage_layout, contract_address=None):
    if title is None:
        if contract_address is None:
            title = "Storage layout"
        else:
            title = f"Storage layout for {contract_address}"
    table = Table(title=title, show_header=True, header_style="bold magenta")
    table.add_column("Name")
    table.add_column("Type", style='dim')
    table.add_column("Slot", style='dim')
    table.add_column("Offset", style='dim')
    table.add_column("Value")
    table.add_column("Contract")

    for storage_value in sorted(storage_layout['storage'], key=lambda x: int(x['slot'])):
        type = storage_value['type']
        value = read_storage_typed_value(read_storage, storage_layout, storage_value)
        table.add_row(
            storage_value['label'],
            storage_layout['types'][type]['label'],
            str(int(storage_value['slot'])),
            str(int(storage_value['offset'])),
            repr(value),
            os.path.basename(storage_value['contract']),
        )
    return table

def get_storage_layout_table_for(read_storage, contract_address: HexBytes):
    contract_address = normalize_contract_address(contract_address)
    registry = contract_registry()
    contract = registry.get(contract_address)
    if contract is None:
        return None
    storage_layout = contract.metadata.storage_layout
    if storage_layout is None:
        return None
    return _get_storage_layout_table_for(read_storage, f"Storage layout as interpreted by {contract_address}", storage_layout, contract_address)

def get_storage_layout_table(read_storage, code_contract_address, storage_contract_address):
    table_code: Table = get_storage_layout_table_for(read_storage, code_contract_address)
    if code_contract_address == storage_contract_address:
        return table_code
    table_storage: Table = get_storage_layout_table_for(read_storage, storage_contract_address)
    if table_code is None and table_storage is None:
        return None
    if table_code is None:
        return table_storage
    if table_storage is None:
        return table_code

    table = Table(title="Storage layout", show_header=True, header_style="bold magenta")
    table.add_column("Contract")
    table.add_column("Storage")
    table.add_row('Code', table_code)
    table.add_row('Storage', table_storage)
    return table

def get_config(wallet_id):
    # Parse file using ConfigParser
    return get_wallet(wallet_id)

class CallFrame():
    def __init__(self, address, msg_sender, tx_origin, value, calltype, callsite):
        # Initialize attributes with args
        self.address = address
        self.msg_sender = msg_sender
        self.tx_origin = tx_origin
        self.value = value
        self.calltype = calltype
        self.callsite = callsite

# Save the original implementation of the function that extracts the message sender
ORIGINAL_extract_transaction_sender = eth._utils.transactions.extract_transaction_sender

class EthDbgShell(cmd.Cmd):

    prompt = f'\001\033[1;31m\002ethdbg➤\001\033[0m\002 '

    def __init__(self, wallet_conf, w3, debug_target, ethdbg_cfg, breaks=None, **kwargs):
        # call the parent class constructor
        super().__init__(**kwargs)
    
        # The config for ethdbg
        self.tty_rows, self.tty_columns = get_terminal_size()
        self.wallet_conf = wallet_conf
        self.account = Account.from_key(self.wallet_conf.private_key)

        self.show_opcodes_desc = ethdbg_cfg['show_opcodes_desc'] if 'show_opcodes_desc' in ethdbg_cfg.keys() else True
        
        # EVM stuff
        self.w3 = w3

        self.debug_target: TransactionDebugTarget = debug_target
        self.debug_target.set_defaults(
            gas=6_000_000, # silly default value
            gas_price=(10 ** 9) * 1000,
            value=0,
            calldata='',
            to='0x0',
            origin=self.debug_target.source_address,
            sender=self.debug_target.source_address,
 nonce=self.w3.eth.get_transaction_count(self.debug_target.source_address),
        )

        # The *CALL trace between contracts
        self.callstack = []

        self.root_tree_node = Tree(self.debug_target._target_address)
        self.curr_tree_node = self.root_tree_node
        self.list_tree_nodes = [self.curr_tree_node]

        # Recording here the SSTOREs, the dictionary is organized
        # per account so we can keep track of what storages slots have
        # been modified for every single contract that the transaction touched
        self.sstores = {}
        self.hide_sstores = ethdbg_cfg['hide_sstores'] if 'hide_sstores' in ethdbg_cfg.keys() else False
        # Recording here the SLOADs, the dictionary is organized
        # per account so we can keep track of what storages slots have
        # been modified for every single contract that the transaction touched
        self.sloads = {}
        self.hide_sloads = ethdbg_cfg['hide_sloads'] if 'hide_sloads' in ethdbg_cfg.keys() else False

        # Debugger state
        # ==============
        #  Whether the debugger is running or not
        self.started = False
        #  Breakpoints PCs
        self.breakpoints: List[Breakpoint] = breaks if breaks else list()

        # Used for finish command
        self.temp_break_finish = False
        self.finish_curr_stack_depth = None

        #  History of executed opcodes
        self.history = list()
        #  The computation object of py-evm
        self.comp = None
        #  The name of the fork we are using
        self.vm_fork_name = ''
        # The current opcode
        self.curr_opcode = None
        #  Used for step command
        self.temp_break = False
        #  Whether we want to display the execute ops
        self.log_op = False
        # Whether we want to stop on RETURN/STOP operations
        self.stop_on_returns = ethdbg_cfg['stop_on_returns'] if 'stop_on_returns' in ethdbg_cfg.keys() else False
        # List of addresses of contracts that reverted
        self.reverted_contracts = set()

    def precmd(self, line):
        # Check if the command is valid, if yes, we save it
        if line != None and line != '' and "do_" + line.split(' ')[0] in [c for c in self.get_names() if "do" in c]:
            save_cmds_history(line)
        return line

    # === DECORATORS ===
    def only_when_started(func):
        def wrapper(self, *args, **kwargs):
            if self.started:
                return func(self, *args, **kwargs)
            else:
                print("You need to start the debugger first. Use 'start' command")
        return wrapper

    # === COMMANDS ===
    def do_chain(self, arg):
        print(f'{self.debug_target.chain}@{self.debug_target.block_number}:{self.w3.provider.endpoint_uri}')

    def do_options(self, arg):
        print(f'chain: {self.debug_target.chain}@{self.debug_target.block_number}')
        print(f'w3-endpoint: {self.w3.provider.endpoint_uri}')
        print(f'full-context: {self.debug_target.full_context}')
        print(f'log_ops: {self.log_op}')
        print(f'stop_on_returns: {self.stop_on_returns}')
        print(f'hide_sstores: {self.hide_sstores}')
        print(f'hide_sloads: {self.hide_sloads}')


    def do_block(self, arg):
        if arg and not self.started:
            self.debug_target.block_number = int(arg,10)
        print(f'{self.debug_target.block_number}')

    def do_account(self, arg):
        if self.debug_target.debug_type == "replay":
            print(f'{self.debug_target.source_address} (impersonating)')
        else:
            print(f'{self.debug_target.source_address}')

    def do_target(self, arg):
        # Check if there is an argument
        # (as of now, once the target is set, you cannot unset it)
        if arg and not self.started:
            self.debug_target.target_address = arg
        else:
            print(f'{self.debug_target.target_address}')

    def do_hextostr(self, arg):
        try:
            print(f'"{HexBytes(arg).decode("utf-8")}"')
        except Exception:
            print(f'Invalid hex string')

    def do_guessfuncid(self, arg):
        try:
            res = decode_function_input(None, arg, guess=True)
            if res is None:
                print(f'Could not retrieve function signature :(')
                return
            _contract, _metadata, _decoded_func = res
            sig, args = _decoded_func
            print(f" → {sig}({', '.join(map(repr,args))})")
        except Exception as e:
            print(f'Could not retrieve function signature :(')
            print(f'{RED_COLOR}{e}{RESET_COLOR}')

    do_guess = do_guessfuncid

    def do_funcid(self, arg):
        arg = arg.encode('utf-8')
        k = sha3.keccak_256()
        k.update(arg)
        print("Function signature: 0x{}".format(k.hexdigest()[0:8]))

    def do_value(self, arg):
        if arg and not self.started:
            self.debug_target.value = int(arg,10)
        else:
            print(f'{self.debug_target.value}')

    def do_gas(self, arg):
        if arg and not self.started:
            self.debug_target.gas = int(arg,10)
        else:
            print(f'{self.debug_target.gas} wei')

    def do_start(self, arg):

        # Check if the target address is a contract!
        if self.debug_target.target_address is not None:
            if self.w3.eth.get_code(self.debug_target.target_address, self.debug_target.block_number) == b'':
                print(f"{RED_COLOR}Target address {self.debug_target.target_address} of transaction is not a contract {RESET_COLOR}")
                sys.exit(0)

        if self.started:
            answer = input("Debugger already started. Do you want to restart the debugger? [y/N] ")
            if answer.lower() == 'y':
                raise RestartDbgException()
            return
        if self.debug_target.target_address == "0x0":
            print("No target set. Use 'target' command to set it.")
            return
        if not self.debug_target.calldata and self.started == False:
            print("No calldata set. Proceeding with empty calldata.")

        if self.debug_target.debug_type == "replay":
            analyzer = Analyzer.from_block_number(self.w3, self.debug_target.block_number)
            vm = analyzer.vm

            if self.debug_target.full_context:
                block = self.w3.eth.get_block(self.debug_target.block_number)
                num_prev_txs = len(block["transactions"][0:self.debug_target.transaction_index])
                print(f'Applying previous {num_prev_txs} transactions...')

                with alive_bar(num_prev_txs) as bar:
                    # Now we need to get the position of the transaction in the block
                    for prev_tx in block["transactions"][0:self.debug_target.transaction_index]:

                        prev_tx_target = TransactionDebugTarget(self.w3)
                        prev_tx_target.replay_transaction(prev_tx)
                        prev_tx_target.set_default('fork', vm.fork)
                        txn = prev_tx_target.get_transaction_dict()

                        def extract_transaction_sender(source_address, transaction: SignedTransactionAPI) -> Address:
                            return bytes(HexBytes(source_address))
                        eth.vm.forks.frontier.transactions.extract_transaction_sender = functools.partial(extract_transaction_sender, prev_tx_target.source_address)

                        raw_txn = bytes(self.account.sign_transaction(txn).rawTransaction)
                        txn = vm.get_transaction_builder().decode(raw_txn)
                        #txn, receipt, _ = analyzer.next_transaction()
                        receipt, comp = vm.apply_transaction(
                            header=vm.get_header(),
                            transaction=txn,
                        )
                        bar()

            analyzer.hook_vm(self._myhook)
        else:
            # get the analyzer
            analyzer = Analyzer.from_block_number(self.w3, self.debug_target.block_number, hook=self._myhook)
            vm = analyzer.vm
            vm.state.set_balance(to_canonical_address(self.account.address), 100000000000000000000000000)

        if self.debug_target.debug_type == "replay":

            def extract_transaction_sender(source_address, transaction: SignedTransactionAPI) -> Address:
                return bytes(HexBytes(source_address))
            eth.vm.forks.frontier.transactions.extract_transaction_sender = functools.partial(extract_transaction_sender, self.debug_target.source_address)
        else:
            eth._utils.transactions.extract_transaction_sender = ORIGINAL_extract_transaction_sender

        if self.debug_target.custom_balance:
            vm.state.set_balance(to_canonical_address(self.debug_target.source_address), int(self.debug_target.custom_balance))

        assert self.debug_target.fork is None or self.debug_target.fork == vm.fork
        self.vm_fork_name = vm.fork

        self.debug_target.set_default('fork', vm.fork)
        txn = self.debug_target.get_transaction_dict()
        raw_txn = bytes(self.account.sign_transaction(txn).rawTransaction)

        txn = vm.get_transaction_builder().decode(raw_txn)

        self.started = True

        origin_callframe = CallFrame(
            '0x'+self.debug_target.target_address.replace('0x','').zfill(40),
            self.debug_target.source_address,
            self.debug_target.source_address,
            self.debug_target.value,
            "-",
            "-")
        self.callstack.append(origin_callframe)

        self.temp_break = True

        try:
            receipt, comp = vm.apply_transaction(
                header=vm.get_header(),
                transaction=txn,
            )
        except eth.exceptions.InsufficientFunds:
            print(f'❌ ERROR: Insufficient funds for account {self.debug_target.source_address}')
            sys.exit(0)
        except RestartDbgException:
            # If it's our restart, let's just re-raise it.
            raise RestartDbgException()
        except Exception as e:
            if "Account Balance cannot be negative" in str(e):
                print(f'❌ ERROR: Insufficient funds for account {self.debug_target.source_address}. Try with option --balance.')
                sys.exit(0)
            else:
                # Otherwise, something is terribly wrong, print and exit.
                print(f'❌ Transaction validation error: {e}')
                raise e

        # Overwrite the origin attribute
        comp.transaction_context._origin = to_canonical_address(self.debug_target.source_address)

        if hasattr(comp, 'error'):
            if type(comp.error) == eth.exceptions.OutOfGas:
                self._display_context(cmdloop=False, with_message=f'❌ {RED_BACKGROUND} ERROR: Out Of Gas{RESET_COLOR}')
            elif type(comp.error) == eth.exceptions.Revert:
                self._handle_revert()
                # Grab only the printable characters from the rever error
                revert_error = comp.error.args[0].decode('ascii', 'ignore')
                revert_error = ''.join([c for c in revert_error if c.isprintable()])
                self._display_context(cmdloop=False, with_message=f'❌ {RED_BACKGROUND} ERROR: Reverted: {revert_error}{RESET_COLOR}')
        else:
            self._display_context(cmdloop=False, with_message=f'✔️ {GREEN_BACKGROUND} Execution Terminated!{RESET_COLOR}')

    def do_context(self, arg):
        if self.started:
            metadata_view = self._get_metadata()
            print(metadata_view)
            disass_view = self._get_disass()
            print(disass_view)
            source_view = self._get_source_view()
            if source_view is not None:
                print(source_view)
            stack_view = self._get_stack()
            print(stack_view)
            callstack_view = self._get_callstack()
            print(callstack_view)
            storage_layout_view = self._get_storage_layout_view()
            if storage_layout_view is not None:
                print(storage_layout_view)
            storage_view = self._get_storage()
            print(storage_view)
        else:
            quick_view = self._get_quick_view(arg)
            print(quick_view)

    def do_calldata(self, arg):
        if arg and not self.started:
            try:
                self.debug_target.calldata = arg
            except Exception:
                print(f'Invalid calldata: {arg}')
        elif not arg and not self.started:
            print(f'{self.debug_target.calldata}')
        else:
            print(f'{self.comp.msg.data.hex()}')

    def do_weitoeth(self, arg):
        try:
            print(f'{int(arg) / 10**18} ETH')
        except Exception:
            print(f'Invalid wei amount')

    def do_ethtowei(self, arg):
        try:
            print(f'{int(float(arg) * 10**18)} wei')
        except Exception:
            print(f'Invalid ETH amount')

    def do_storageat(self, arg):
        if not arg:
            print("Usage: storageat [<address>:]<slot>[:<count>]")
            return

        address = None
        if ':' in arg:
            address, slot = arg.split(':')
            address = HexBytes(address)
            slot = int(slot, 16)
        else:
            address = self.comp.msg.storage_address if self.started else self.debug_target.target_address
            slot = int(arg, 16)
        try:
            if self.started:
                value_read = self.comp.state.get_storage(address, slot)
            else:
                value_read = self.w3.eth.get_storage_at(address, slot, self.debug_target.block_number)
        except Exception as e:
            print("Something went wrong while fetching storage:")
            print(f' Error: {RED_COLOR}{e}{RESET_COLOR}')

        value_read = "0x" + hex(value_read).replace("0x",'').zfill(64)
        print(f' {CYAN_COLOR}[r]{RESET_COLOR} Slot: {hex(slot)} | Value: {value_read}')

    def do_callhistory(self, arg):
        rich_print(self.root_tree_node)

    @only_when_started
    def do_sstores(self, arg):
         # Check if there is an argument
        if arg and arg in self.sstores.keys():
            sstores_account = self.sstores[arg]
            for sstore_slot, sstore_val in sstores_account.items():
                if arg not in self.reverted_contracts:
                    print(f' {YELLOW_COLOR}[w]{RESET_COLOR} Slot: {sstore_slot} | Value: {sstore_val}')
                else:
                    _log = f' [w] Slot: {sstore_slot} | Value: {sstore_val}'
                    res = ''
                    for c in _log:
                        res = res + c + STRIKETHROUGH
                    print(f'{res} ❌')
        else:
            for ref_account, sstores in self.sstores.items():
                print(f'Account: {BOLD_TEXT}{BLUE_COLOR}{ref_account}{RESET_COLOR}:')
                for sstore_slot, sstore_val in sstores.items():
                    print(f' {YELLOW_COLOR}[w]{RESET_COLOR} Slot: {sstore_slot} | Value: {sstore_val}')

    @only_when_started
    def do_sloads(self, arg):
        if arg and arg in self.sloads.keys():
            sloads_account = self.sloads[arg]
            for sload_slot, sload_val in sloads_account.items():
                print(f' {CYAN_COLOR}[r]{RESET_COLOR} Slot: {sload_slot} | Value: {HexBytes(sload_val).hex()}')
        else:
            for ref_account, sloads in self.sloads.items():
                print(f'Account: {BOLD_TEXT}{BLUE_COLOR}{ref_account}{RESET_COLOR}:')
                for sload_slot, sload_val in sloads.items():
                    print(f' {CYAN_COLOR}[r]{RESET_COLOR} Slot: {sload_slot} | Value: {HexBytes(sload_val).hex()}')

    def do_breaks(self,arg):
        # Print all the breaks
        for b_idx, b in enumerate(self.breakpoints):
            print(f'Breakpoint {b_idx} | {b}')

    def do_break(self, arg):
        # parse the arg
        break_args = arg.split(",")
        try:
            bp = Breakpoint(break_args)
            if bp.signature not in [b.signature for b in self.breakpoints]:
                self.breakpoints.append(bp)
        except InvalidBreakpointException:
            print(f'{RED_COLOR}Invalid breakpoint{RESET_COLOR}:')
            print(f'{RED_COLOR} Valid syntax is: <what><when><value>,<what><when><value>{RESET_COLOR}')
            print(f'{RED_COLOR}  <when> in (=, ==, !=, >, <, >=, <=){RESET_COLOR}')
            print(f'{RED_COLOR}  <what> in (addr, saddr, op, pc, value){RESET_COLOR}')

    def do_tbreak(self, arg):
        # parse the arg
        break_args = arg.split(",")
        try:
            bp = Breakpoint(break_args, temp=True)
            if bp.signature not in [b.signature for b in self.breakpoints]:
                self.breakpoints.append(bp)
        except InvalidBreakpointException:
            print(f'{RED_COLOR}Invalid breakpoint{RESET_COLOR}:')
            print(f'{RED_COLOR} Valid syntax is: <what><when><value>,<what><when><value>{RESET_COLOR}')
            print(f'{RED_COLOR}  <when> in (=, ==, !=, >, <, >=, <=){RESET_COLOR}')
            print(f'{RED_COLOR}  <what> in (addr, saddr, op, pc, value){RESET_COLOR}')

    do_b = do_break
    do_tb = do_tbreak

    @only_when_started
    def do_finish(self, arg):
        if len(self.callstack) > 1:
            self.temp_break_finish = True
            self.finish_curr_stack_depth = len(self.callstack)
            self._resume()


    def do_ipython(self, arg):
        import IPython; IPython.embed()

    @only_when_started
    def do_continue(self, arg):
        self._resume()

    do_c = do_continue
    do_cont = do_continue

    @only_when_started
    def do_step(self, arg):
        if self.started == False:
            print("No execution started. Use 'start' command to start it.")
            return
        else:
            # We set the breakpoint to the next instruction
            self.temp_break = True
            self._resume()

    do_s = do_step

    def do_next(self, arg):
        pc = self.curr_pc
        with self.comp.code.seek(pc):
            opcode_bytes = self.comp.code.read(64) # max 32 byte immediate + 32 bytes should be enough, right???

        assert self.debug_target.fork is not None

        if opcode_bytes:
            insn: Instruction = disassemble_one(opcode_bytes, pc=pc, fork=self.debug_target.fork)
            assert insn is not None, "64 bytes was not enough to disassemble?? or this is somehow an invalid opcode??"
            assert insn.mnemonic == self.curr_opcode.mnemonic, "disassembled opcode does not match the opcode we're currently executing??"
            next_pc = hex(pc + insn.size)
            curr_account_code = normalize_contract_address(self.comp.msg.code_address)
            self.do_tbreak(f'pc={next_pc},addr={curr_account_code}')
            self._resume()

    def do_clear(self, arg):
        if arg:
            if arg == "all":
                self.breakpoints = []
                print("All breakpoints cleared")
            else:
                # Check if arg is a hex number
                try:
                    arg = int(arg,16)
                    del self.breakpoints[arg]
                    print(f'Breakpoint cleared at {arg}')
                except Exception:
                    print("Invalid breakpoint")

    do_del = do_clear

    def do_log_op(self, arg):
        self.log_op = not self.log_op
        print(f'Logging opcodes: {self.log_op}')

    def do_hide_sloads(self, arg):
        self.hide_sloads = not self.hide_sloads
        print(f'Hiding sloads: {self.hide_sloads}')

    def do_hide_sstores(self, arg):
        self.hide_sstores = not self.hide_sstores
        print(f'Hiding sstores: {self.hide_sstores}')

    def do_stop_on_returns(self, arg):
        self.stop_on_returns = not self.stop_on_returns
        print(f'Stopping on returns: {self.stop_on_returns}')

    def do_quit(self, arg):
        sys.exit()

    def do_EOF(self, arg):
        # quit if user says yes or hits ctrl-d again
        try:
            if input(f" {BLUE_COLOR}[+] EOF, are you sure you want to quit? (y/n) {RESET_COLOR}") == 'y':
                self.do_quit(arg)
        except EOFError:
            self.do_quit(arg)
        except KeyboardInterrupt:
            pass

    def do_clear(self, arg):
        # just clear the screen
        os.system('clear')

    do_q = do_quit

    @only_when_started
    def do_memory(self, args):
        read_args = args.split(" ")
        if len(read_args) != 2:
            print("Usage: memory <offset> <length>")
            return
        else:
            try:
                # check  if lenght is a decimal number or hex number
                offset, length = args.split(" ")[0], args.split(" ")[1]

                if read_args[1].startswith("0x"):
                    length = int(read_args[1],16)
                else:
                    length = int(read_args[1],10)
                data = self.comp._memory.read(int(offset,16), length)
                hexdump(data.tobytes())
            except Exception as e:
                print(f'{RED_COLOR}Error reading memory: {e}{RESET_COLOR}')

    # === INTERNALS ===

    def _resume(self):
        raise ExitCmdException()

    def _handle_revert(self):
        # We'll mark the sstores as reverted
        curr_storage_contract = normalize_contract_address(self.comp.msg.storage_address)
        curr_code_contracts = normalize_contract_address(self.comp.msg.code_address)

        reverting_contracts = [curr_storage_contract, curr_code_contracts]
        self.reverted_contracts.add(curr_storage_contract)
        self.reverted_contracts.add(curr_code_contracts) # this is useless but ok

        worklist = set()
        for x in self.list_tree_nodes:
            worklist.add(x)

        while len(worklist) != 0:
            node = worklist.pop()
            if curr_storage_contract in node.label or curr_code_contracts in node.label:
                offset = node.label.find(curr_storage_contract)
                if offset == -1:
                    offset = node.label.find(curr_code_contracts)
                assert(offset != -1)

                new_label = node.label[:offset]

                for c in node.label[offset:]:
                    if c.isascii():
                        new_label = new_label + c + STRIKETHROUGH
                node.label = new_label + ' (revert) ❌'
            for child in node.children:
                worklist.add(child)

    def _handle_out_of_gas(self):
        # We'll mark the sstores as reverted
        curr_storage_contract =  normalize_contract_address(self.comp.msg.storage_address)
        curr_code_contracts = normalize_contract_address(self.comp.msg.code_address)

        reverting_contracts = [curr_storage_contract, curr_code_contracts]
        self.reverted_contracts.add(curr_storage_contract)
        self.reverted_contracts.add(curr_code_contracts) # this is useless but ok

        worklist = set()
        for x in self.list_tree_nodes:
            worklist.add(x)

        while len(worklist) != 0:
            node = worklist.pop()
            if curr_code_contracts in node.label:
                offset = node.label.find(curr_storage_contract)
                if offset == -1:
                    offset = node.label.find(curr_code_contracts)
                assert(offset != -1)

                new_label = node.label[:offset]

                for c in node.label[offset:]:
                    if c.isascii():
                        new_label = new_label + c + STRIKETHROUGH
                node.label = new_label + ' (out of gas) 🪫'
            for child in node.children:
                worklist.add(child)

    def _get_callstack(self):
        message = f"{GREEN_COLOR}Callstack {RESET_COLOR}"

        fill = HORIZONTAL_LINE
        align = '<'
        width = max(self.tty_columns,0)

        title = f'{message:{fill}{align}{width}}'+'\n'

        calls_view = ''
        max_call_opcode_length = max(len('CallType'), max((len(call.calltype) for call in self.callstack), default=0))
        max_pc_length = max(len('CallSite'), max((len(call.callsite) for call in self.callstack), default=0))
        calltype_string_legend = 'CallType'.ljust(max_call_opcode_length)
        callsite_string_legend = 'CallSite'.rjust(max_pc_length)
        legend = f'{"[ Legend: Address":44} | {calltype_string_legend} | {callsite_string_legend} | {"msg.sender":44} | msg.value ]\n'
        for call in self.callstack[::-1]:
            calltype_string = f'{call.calltype}'
            if call.calltype == "CALL":
                color = PURPLE_COLOR
            elif call.calltype == "DELEGATECALL" or call.calltype == "CODECALL":
                color = RED_COLOR
            elif call.calltype == "STATICCALL":
                color = BLUE_COLOR
            elif call.calltype == "CREATE":
                color = GREEN_COLOR
            elif call.calltype == "CREATE2":
                color = PURPLE_COLOR
            else:
                color = ''
            calltype_string = calltype_string.ljust(max_call_opcode_length)
            callsite_string = call.callsite.rjust(max_pc_length)
            call_addr = call.address
            msg_sender = call.msg_sender
            calls_view += f'{call_addr:44} | {color}{calltype_string}{RESET_COLOR} | {callsite_string} | {msg_sender:44} | {call.value} \n'

        return title + legend + calls_view

    def _get_disass(self):
        message = f"{GREEN_COLOR}Disassembly {RESET_COLOR}"

        fill = HORIZONTAL_LINE
        align = '<'
        width = max(self.tty_columns,0)

        title = f'{message:{fill}{align}{width}}'+'\n'

        # print the last 10 instructions, this can be configurable later
        _history = ''
        rev_history = self.history[::-1]
        curr_ins = rev_history[0]
        slice_history = rev_history[1:3]
        slice_history = slice_history[::-1]
        for insn in slice_history:
            _history += '  ' + insn + '\n'
        _history += f'→ {RED_COLOR}{self.history[-1]}{RESET_COLOR}' + '\n'

        # Let's see what's next
        pc = self.curr_pc
        with self.comp.code.seek(pc):
            opcode_bytes = self.comp.code.read(64) # max 32 byte immediate + 32 bytes should be enough, right???

        assert self.debug_target.fork is not None

        if opcode_bytes:
            insn: Instruction = disassemble_one(opcode_bytes, pc=pc, fork=self.debug_target.fork)
            assert insn is not None, "64 bytes was not enough to disassemble?? or this is somehow an invalid opcode??"
            assert insn.mnemonic == self.curr_opcode.mnemonic, "disassembled opcode does not match the opcode we're currently executing??"

        _next_opcodes_str = f''

        # print 5 instruction after
        for _ in range(0,5):
            pc += insn.size
            with self.comp.code.seek(pc):
                opcode_bytes = self.comp.code.read(64)
            if opcode_bytes:
                insn: Instruction = disassemble_one(opcode_bytes, pc=pc, fork=self.debug_target.fork)
                assert insn is not None, "64 bytes was not enough to disassemble?? or this is somehow an invalid opcode??"
                hex_bytes = ' '.join(f'{b:02x}' for b in insn.bytes[:5])
                if insn.size > 5: hex_bytes += ' ...'
                if self.show_opcodes_desc:
                    _next_opcodes_str += f'  {pc:#06x}  {hex_bytes:18} {str(insn):20}    // {insn.description}\n'
                else:
                    _next_opcodes_str += f'  {pc:#06x}  {hex_bytes:18} {str(insn):20}\n'
            else:
                break

        return title + _history + _next_opcodes_str

    def _get_metadata(self):
        message = f"{GREEN_COLOR}Metadata {RESET_COLOR}"

        fill = HORIZONTAL_LINE
        align = '<'
        width = max(self.tty_columns,0)

        title = f'{message:{fill}{align}{width}}'+'\n'

        # Fetching the metadata from the state of the computation
        try:
            curr_account_code = normalize_contract_address(self.comp.msg.code_address)
        except Exception as e:
            curr_account_code = '0x'

        curr_account_storage = normalize_contract_address(self.comp.msg.storage_address)
        curr_origin = normalize_contract_address(self.comp.transaction_context.origin)
        curr_balance = self.comp.state.get_balance(self.comp.msg.storage_address)
        curr_balance_eth = int(curr_balance) / 10**18

        gas_remaining = self.comp.get_gas_remaining() + self.comp.get_gas_refund()
        gas_used = self.debug_target.gas - self.comp.get_gas_remaining() - self.comp.get_gas_refund()
        gas_limit = self.comp.state.gas_limit

        _metadata = f'EVM fork: [[{self.debug_target.fork}]] | Block: {self.debug_target.block_number} | Origin: {curr_origin}\n'
        _metadata += f'Current Code Account: {YELLOW_COLOR}{curr_account_code}{RESET_COLOR} | Current Storage Account: {YELLOW_COLOR}{curr_account_storage}{RESET_COLOR}\n'
        _metadata += f'💰 Balance: {curr_balance} wei ({curr_balance_eth} ETH) | ⛽ Gas Used: {gas_used} | ⛽ Gas Remaining: {gas_remaining} '

        return title + _metadata

    def _get_stack(self, attempt_decode=False):
        message = f"{GREEN_COLOR}Stack {RESET_COLOR}"

        fill = HORIZONTAL_LINE
        align = '<'
        width = max(self.tty_columns,0)

        title = f'{message:{fill}{align}{width}}'+'\n'

        _stack = ''

        for entry_slot, entry in enumerate(self.comp._stack.values[::-1][0:10]):
            entry_type = entry[0]
            entry_val = entry[1]

            entry_val = int.from_bytes(HexBytes(entry_val), byteorder='big')

            _stack += f'{hex(entry_slot)}│ {"0x"+hex(entry_val).replace("0x", "").zfill(64)}\n'

        # Decoration of the stack given the current opcode
        if self.curr_opcode.mnemonic == "SLOAD":
            _more_stack = _stack.split("\n")[1:]
            _stack = _stack.split("\n")[0:1]

            slot_id = int(_stack[0].split(" ")[1],16)
            _stack[0] += f'{BRIGHT_YELLOW_COLOR} (slot_id) {RESET_COLOR}'
            value_at_slot = self.comp.state.get_storage(self.comp.msg.storage_address, slot_id)
            value_at_slot = "0x"+hex(value_at_slot).replace("0x",'').zfill(64)
            _stack[0] += f'→ {ORANGE_COLOR}{value_at_slot}{RESET_COLOR}'

            return title + '\n'.join(_stack) + '\n' + '\n'.join(_more_stack)

        elif self.curr_opcode.mnemonic == "SSTORE":
            _more_stack = _stack.split("\n")[2:]
            _stack = _stack.split("\n")[0:2]

            slot_id = int(_stack[0].split(" ")[1],16)
            new_value = int(_stack[1].split(" ")[1],16)
            new_value = "0x"+hex(new_value).replace("0x",'').zfill(64)
            _stack[0] += f'{BRIGHT_YELLOW_COLOR} (slot_id) {RESET_COLOR}'
            value_at_slot = self.comp.state.get_storage(self.comp.msg.storage_address, slot_id)
            value_at_slot = "0x"+hex(value_at_slot).replace("0x",'').zfill(64)
            _stack[0] += f'→ {ORANGE_COLOR}{value_at_slot}{RESET_COLOR}'
            _stack[1] += f'{BRIGHT_YELLOW_COLOR} (slotval){RESET_COLOR} → '

            _diff_string = ''
            for idx, byte in enumerate(value_at_slot):
                if byte != new_value[idx]:
                    _diff_string += f'{RED_COLOR}{new_value[idx]}{RESET_COLOR}'
                else:
                    _diff_string += f'{GREEN_COLOR}{byte}{RESET_COLOR}'
            _stack[1] += _diff_string

            # do a diff between the value at the slot and the new value and print
            # every byte of the new value in green if they are the same, in red if they are different

            return title + '\n'.join(_stack) + '\n' + '\n'.join(_more_stack)

        elif self.curr_opcode.mnemonic == "CALL":
            _more_stack = _stack.split("\n")[7:]
            _stack = _stack.split("\n")[0:7]

            gas = int(_stack[0].split(" ")[1],16)
            value = int(_stack[2].split(" ")[1],16)
            argOffset =  int(_stack[3].split(" ")[1],16)
            argSize   =  int(_stack[4].split(" ")[1],16)

            argSizeHuge = False

            if argSize > 20:
                argSize = 20
                argSizeHuge = True

            _stack[0] += f' ({gas}) {BRIGHT_YELLOW_COLOR} (gas) {RESET_COLOR}'
            _stack[1] += f'{BRIGHT_YELLOW_COLOR} (target) {RESET_COLOR}'
            _stack[2] += f' ({value}){BRIGHT_YELLOW_COLOR} (value) {RESET_COLOR}'
            _stack[3] += f'{BRIGHT_YELLOW_COLOR} (argOffset) {RESET_COLOR}'
            _stack[4] += f'{BRIGHT_YELLOW_COLOR} (argSize) {RESET_COLOR}'

            memory_at_offset = self.comp._memory.read(argOffset,argSize).hex()

            if argSizeHuge:
                _stack[3] += f'{ORANGE_COLOR}→ {GREEN_COLOR}{BOLD_TEXT}[0x{memory_at_offset[0:8]}]{RESET_COLOR}{ORANGE_COLOR}{memory_at_offset[8:]}...{RESET_COLOR}'
            else:
                _stack[3] += f'{ORANGE_COLOR}→ {GREEN_COLOR}{BOLD_TEXT}[0x{memory_at_offset[0:8]}]{RESET_COLOR}{ORANGE_COLOR}{memory_at_offset[8:]}{RESET_COLOR}'

            _stack[5] += f'{BRIGHT_YELLOW_COLOR} (retOffset) {RESET_COLOR}'
            _stack[6] += f'{BRIGHT_YELLOW_COLOR} (retSize) {RESET_COLOR}'

            return title + '\n'.join(_stack) + '\n' + '\n'.join(_more_stack)
        elif self.curr_opcode.mnemonic == "DELEGATECALL":
            _more_stack = _stack.split("\n")[7:]
            _stack = _stack.split("\n")[0:7]

            gas = int(_stack[0].split(" ")[1],16)
            argOffset =  int(_stack[2].split(" ")[1],16)
            argSize   =  int(_stack[3].split(" ")[1],16)

            argSizeHuge = False

            if argSize > 50:
                argSize = 50
                argSizeHuge = True

            _stack[0] += f' ({gas}) {BLUE_COLOR} (gas) {RESET_COLOR}'
            _stack[1] += f'{BLUE_COLOR} (target) {RESET_COLOR}'
            _stack[2] += f'{BLUE_COLOR} (argOffset) {RESET_COLOR}'
            _stack[3] += f'{BLUE_COLOR} (argSize) {RESET_COLOR}'

            memory_at_offset = self.comp._memory.read(argOffset,argSize).hex()

            if argSizeHuge:
                _stack[2] += f'{ORANGE_COLOR}→ {GREEN_COLOR}{BOLD_TEXT}[0x{memory_at_offset[0:8]}]{RESET_COLOR}{ORANGE_COLOR}{memory_at_offset[8:]}...{RESET_COLOR}'
            else:
                _stack[2] += f'{ORANGE_COLOR}→ {GREEN_COLOR}{BOLD_TEXT}[0x{memory_at_offset[0:8]}]{RESET_COLOR}{ORANGE_COLOR}{memory_at_offset[8:]}{RESET_COLOR}'

            _stack[4] += f'{BLUE_COLOR} (retOffset) {RESET_COLOR}'
            _stack[5] += f'{BLUE_COLOR} (retSize) {RESET_COLOR}'

            return title + '\n'.join(_stack) + '\n' + '\n'.join(_more_stack)

        elif self.curr_opcode.mnemonic == "STATICCALL":
            _more_stack = _stack.split("\n")[7:]
            _stack = _stack.split("\n")[0:7]

            gas = int(_stack[0].split(" ")[1],16)
            argOffset =  int(_stack[2].split(" ")[1],16)
            argSize   =  int(_stack[3].split(" ")[1],16)

            argSizeHuge = False

            if argSize > 50:
                argSize = 50
                argSizeHuge = True

            _stack[0] += f' ({gas}) {BLUE_COLOR} (gas) {RESET_COLOR}'
            _stack[1] += f'{BLUE_COLOR} (target) {RESET_COLOR}'
            _stack[2] += f'{BLUE_COLOR} (argOffset) {RESET_COLOR}'
            _stack[3] += f'{BLUE_COLOR} (argSize) {RESET_COLOR}'

            memory_at_offset = self.comp._memory.read(argOffset,argSize).hex()

            if argSizeHuge:
                _stack[2] += f'{ORANGE_COLOR}→ {GREEN_COLOR}{BOLD_TEXT}[0x{memory_at_offset[0:8]}]{RESET_COLOR}{ORANGE_COLOR}{memory_at_offset[8:]}...{RESET_COLOR}'
            else:
                _stack[2] += f'{ORANGE_COLOR}→ {GREEN_COLOR}{BOLD_TEXT}[0x{memory_at_offset[0:8]}]{RESET_COLOR}{ORANGE_COLOR}{memory_at_offset[8:]}{RESET_COLOR}'

            _stack[4] += f'{BLUE_COLOR} (retOffset) {RESET_COLOR}'
            _stack[5] += f'{BLUE_COLOR} (retSize) {RESET_COLOR}'

            return title + '\n'.join(_stack) + '\n' + '\n'.join(_more_stack)
        else:
            return title + _stack


    def _get_storage(self):
        ref_account = normalize_contract_address(self.comp.msg.storage_address)
        message = f"{GREEN_COLOR}Last Active Storage Slots [{ref_account}]{RESET_COLOR}"

        fill = HORIZONTAL_LINE
        align = '<'
        width = max(self.tty_columns,0)

        title = f'{message:{fill}{align}{width}}'+'\n'
        legend = f'[ Legend: Slot Address -> Value ]\n'

        # Iterate over sloads for this account
        _sload_log = ''
        if not self.hide_sloads:
            if ref_account in self.sloads:
                ref_account_sloads = self.sloads[ref_account]
                for slot, val in ref_account_sloads.items():
                    _sload_log += f'{CYAN_COLOR}[r]{RESET_COLOR} {slot} -> {hex(val)}\n'

        _sstore_log = ''
        # Iterate over sstore for this account
        if not self.hide_sstores:
            ref_account = normalize_contract_address(self.comp.msg.storage_address)
            if ref_account in self.sstores:
                ref_account_sstores = self.sstores[ref_account]
                for slot, val in ref_account_sstores.items():
                    _sstore_log += f'{YELLOW_COLOR}[w]{RESET_COLOR} {slot} -> {val}\n'

        return title + legend + _sload_log + _sstore_log

    def _get_quick_view(self, arg):
        # print the current configuration of EthDebugger
        message = f"{GREEN_COLOR}Quick View{RESET_COLOR}"
        fill = HORIZONTAL_LINE
        align = '<'
        width = max(self.tty_columns,0)

        title = f'{message:{fill}{align}{width}}'

        if arg != 'init':
            print(title)

        assert not self.started, "Debugger already started."

        # print the chain context and the transaction context
        print(f'Account: {YELLOW_COLOR}{self.debug_target.source_address}{RESET_COLOR} | Target Contract: {YELLOW_COLOR}{self.debug_target.target_address}{RESET_COLOR}')
        print(f'Chain: {self.debug_target.chain} | Node: {self.w3.provider.endpoint_uri} | Block Number: {self.debug_target.block_number}')
        print(f'Value: {self.debug_target.value} | Gas: {self.debug_target.gas}')

    def _get_source_view(self):
        # import ipdb; ipdb.set_trace()
        message = f"{GREEN_COLOR}Source View{RESET_COLOR}"
        fill = HORIZONTAL_LINE
        align = '<'
        width = max(self.tty_columns,0)

        title = f'{message:{fill}{align}{width}}'

        assert self.started, "Debugger not started yet."

        # print the chain context and the transaction context
        # import ipdb; ipdb.set_trace()
        try:
            source = get_source_code(self.debug_target, self.comp.msg.code_address, self.comp.code.program_counter - 1)
        except Exception as e:
            source = None

        if source is not None:
            return title + '\n' + source
        else:
            return None

    def _get_storage_layout_view(self):
        # import ipdb; ipdb.set_trace()
        message = f"{GREEN_COLOR}Storage Layout{RESET_COLOR}"
        fill = HORIZONTAL_LINE
        align = '<'
        width = max(self.tty_columns,0)

        title = f'{message:{fill}{align}{width}}'

        assert self.started, "Debugger not started yet."

        # print the chain context and the transaction context
        # import ipdb; ipdb.set_trace()
        storage_layout = get_storage_layout_table(
            lambda slot: self.comp.state.get_storage(self.comp.msg.storage_address, slot).to_bytes(32, byteorder='big'),
            self.comp.msg.code_address,
            self.comp.msg.storage_address
            )

        if storage_layout is not None:
            with rich.get_console().capture() as capture:
                rich.print(storage_layout)
            storage_layout = capture.get()
            return title + '\n' + storage_layout + '\n'
        else:
            return None

    def _display_context(self, cmdloop=True, with_message=''):
        metadata_view = self._get_metadata()

        if with_message != '':
            metadata_view += f'\nStatus: {with_message}'

        source_view = self._get_source_view()
        if source_view is not None:
            print(source_view)

        print(metadata_view)
        
        disass_view = self._get_disass()
        print(disass_view)
        
        stack_view = self._get_stack()
        print(stack_view)
        callstack_view = self._get_callstack()
        print(callstack_view)
        storage_layout_view = self._get_storage_layout_view()
        if storage_layout_view is not None:
            print(storage_layout_view)
        storage_view = self._get_storage()
        print(storage_view)

        if cmdloop:
            try:
                self.cmdloop(intro='')
            except ExitCmdException:
                pass
            except RestartDbgException:
                raise RestartDbgException()

    def _myhook(self, opcode: Opcode, computation: ComputationAPI):
        # Store a reference to the computation to make it
        # accessible to the comamnds

        # Overwriting the origin
        computation.transaction_context._origin = to_canonical_address(self.debug_target.source_address)

        self.comp = computation
        self.curr_opcode = opcode

        # the computation.code.__iter__() has already incremented the program counter by 1, account for this
        pc = computation.code.program_counter - 1
        self.curr_pc = pc

        with computation.code.seek(pc):
            opcode_bytes = computation.code.read(64) # max 32 byte immediate + 32 bytes should be enough, right???

        assert self.debug_target.fork is not None
        if opcode_bytes:
            insn: Instruction = disassemble_one(opcode_bytes, pc=pc, fork=self.debug_target.fork)
            assert insn is not None, "64 bytes was not enough to disassemble?? or this is somehow an invalid opcode??"
            if insn.mnemonic != opcode.mnemonic:
                print(f"disassembled opcode does not match the opcode we're currently executing??")
            hex_bytes = ' '.join(f'{b:02x}' for b in insn.bytes[:5])
            if insn.size > 5: hex_bytes += ' ...'
            if self.show_opcodes_desc:
                _opcode_str = f'{pc:#06x}  {hex_bytes:18} {str(insn):20}    // {insn.description}'
            else:
                _opcode_str = f'{pc:#06x}  {hex_bytes:18} {str(insn):20}'
        else:
            _opcode_str = f'{pc:#06x}  {"":18} {opcode.mnemonic:15} [WARNING: no code]'

        if self.log_op:
            print(f'{_opcode_str}')

        self.history.append(_opcode_str)

        if self.temp_break:
            self.temp_break = False
            self._display_context(with_message=f'🎯 {YELLOW_BACKGROUND}Breakpoint [temp] reached{RESET_COLOR}')
        else:
            # BREAKPOINT MANAGEMENT
            for sbpid, sbp in enumerate(self.breakpoints):
                if sbp.eval_bp(self.comp, pc, opcode, self.callstack):
                    if sbp.temp:
                        self.breakpoints.remove(sbp)
                    self._display_context(with_message=f'🎯 {YELLOW_BACKGROUND}Breakpoint [{sbpid}] reached{RESET_COLOR}')

        if self.temp_break_finish and len(self.callstack) < self.finish_curr_stack_depth:
            # Reset finish break condition
            self.temp_break_finish = False
            self.finish_curr_stack_depth = None
            self._display_context(with_message=f'🎯 {YELLOW_BACKGROUND}Breakpoint [finish] reached{RESET_COLOR}')

        elif self.stop_on_returns and (opcode.mnemonic == "STOP" or opcode.mnemonic == "RETURN"):
            self._display_context(with_message=f'🎯 {YELLOW_BACKGROUND}Breakpoint [stop/return] reached{RESET_COLOR}')

        if opcode.mnemonic == "SSTORE":
            ref_account = normalize_contract_address(computation.msg.storage_address)

            slot_id = hex(read_stack_int(computation, 1))
            slot_val = hex(read_stack_int(computation, 2))

            if ref_account not in self.sstores.keys():
                self.sstores[ref_account] = {}
                self.sstores[ref_account][slot_id] = slot_val
            else:
                self.sstores[ref_account][slot_id] = slot_val

        if opcode.mnemonic == "SLOAD":
            ref_account = normalize_contract_address(computation.msg.storage_address)
            slot_id = hex(read_stack_int(computation, 1))

            # CHECK THIS
            slot_val = computation.state.get_storage(computation.msg.storage_address, int(slot_id,16))
            if ref_account not in self.sloads.keys():
                self.sloads[ref_account] = {}
                self.sloads[ref_account][slot_id] = slot_val
            else:
                self.sloads[ref_account][slot_id] = slot_val

        if opcode.mnemonic in CALL_OPCODES:

            if opcode.mnemonic == "CALL":
                contract_target = hex(read_stack_int(computation, 2))
                contract_target = normalize_contract_address(contract_target)
                value_sent = read_stack_int(computation, 3)

                # We gotta parse the callstack according to the *CALL opcode
                new_callframe = CallFrame(
                                        contract_target,
                                        normalize_contract_address(computation.msg.code_address),
                                        normalize_contract_address(computation.transaction_context.origin),
                                        value_sent,
                                        "CALL",
                                        hex(pc)
                                        )

                self.callstack.append(new_callframe)
                new_tree_node = self.curr_tree_node.add(f"{PURPLE_COLOR}CALL{RESET_COLOR} {contract_target}")
                self.curr_tree_node = new_tree_node
                self.list_tree_nodes.append(new_tree_node)

            elif opcode.mnemonic == "DELEGATECALL":
                contract_target = hex(read_stack_int(computation, 2))
                contract_target = normalize_contract_address(contract_target)
                value_sent = 0
                # We gotta parse the callstack according to the *CALL opcode
                new_callframe = CallFrame(
                                        contract_target,
                                        self.callstack[-1].msg_sender,
                                        normalize_contract_address(computation.transaction_context.origin),
                                        value_sent,
                                        "DELEGATECALL",
                                        hex(pc)
                                        )
                self.callstack.append(new_callframe)
                new_tree_node = self.curr_tree_node.add(f"{RED_COLOR}DELEGATECALL{RESET_COLOR} {contract_target}")
                self.curr_tree_node = new_tree_node
                self.list_tree_nodes.append(new_tree_node)

            elif opcode.mnemonic == "STATICCALL":
                contract_target = hex(read_stack_int(computation, 2))
                contract_target = normalize_contract_address(contract_target)

                value_sent = 0
                if int(contract_target,16) not in PRECOMPILED_CONTRACTS.values():
                    # We gotta parse the callstack according to the *CALL opcode
                    new_callframe = CallFrame(
                                            contract_target,
                                            normalize_contract_address(computation.msg.code_address),
                                            normalize_contract_address(computation.transaction_context.origin),
                                            value_sent,
                                            "STATICCALL",
                                            hex(pc)
                                            )
                    self.callstack.append(new_callframe)
                    new_tree_node = self.curr_tree_node.add(f"{BLUE_COLOR}STATICCALL{RESET_COLOR} {contract_target}")
                    self.curr_tree_node = new_tree_node
                    self.list_tree_nodes.append(new_tree_node)
                else:
                    self.curr_tree_node.add(f"{BLUE_COLOR}STATICCALL{RESET_COLOR} {contract_target}")

            elif opcode.mnemonic == "CREATE":
                contract_value = hex(read_stack_int(computation, 1))
                code_offset = hex(read_stack_int(computation, 2))
                code_size = hex(read_stack_int(computation, 3))

                new_callframe = CallFrame(
                    normalize_contract_address(0x0),
                    normalize_contract_address(computation.msg.code_address),
                    normalize_contract_address(computation.transaction_context.origin),
                    contract_value,
                    "CREATE",
                    hex(pc)
                )
                self.callstack.append(new_callframe)
                new_tree_node = self.curr_tree_node.add(f"{GREEN_COLOR}CREATE{RESET_COLOR} 0x0")
                self.curr_tree_node = new_tree_node
                self.list_tree_nodes.append(new_tree_node)

            elif opcode.mnemonic == "CREATE2":
                contract_value = hex(read_stack_int(computation, 1))
                code_offset = hex(read_stack_int(computation, 2))
                code_size = hex(read_stack_int(computation, 3))
                salt = hex(read_stack_int(computation, 4))

                new_callframe = CallFrame(
                    normalize_contract_address(0x0),
                    normalize_contract_address(computation.msg.code_address),
                    normalize_contract_address(computation.transaction_context.origin),
                    contract_value,
                    "CREATE2",
                    hex(pc)
                )
                self.callstack.append(new_callframe)
                new_tree_node = self.curr_tree_node.add(f"{GREEN_COLOR}CREATE2{RESET_COLOR} 0x0")
                self.curr_tree_node = new_tree_node
                self.list_tree_nodes.append(new_tree_node)

            else:
                print(f"Plz add support for {opcode.mnemonic}")

        if opcode.mnemonic in RETURN_OPCODES:
            self.callstack.pop()
            if len(self.list_tree_nodes) > 1:
                old_root = self.list_tree_nodes.pop()
                self.curr_tree_node = self.list_tree_nodes[-1]
        if opcode.mnemonic == "REVERT":
            self._handle_revert()

        # Execute the opcode finally!
        try:
            opcode(computation=computation)
        except eth.exceptions.OutOfGas:
            self._handle_out_of_gas()


    def print_license(self):
        print(f"{YELLOW_COLOR}⧫ {BOLD_TEXT}ethdbg 0.1 ⧫ - The CLI EVM Debugger{RESET_COLOR}")
        print("License: MIT License")
        print("For a copy, see <https://opensource.org/licenses/MIT>")


def main():
    parser = argparse.ArgumentParser()

    # parse optional argument
    parser.add_argument("--txid", help="address of the smart contract we are debugging", default=None)
    parser.add_argument("--full-context", help="weather we should replay the previous txs before the target one", action='store_true')
    parser.add_argument("--sender", help="address of the sender", default=None)
    parser.add_argument("--balance", help="set a custom balance for the sender", default=None)
    parser.add_argument("--value",  help="amount of ETH to send", default=None)
    parser.add_argument("--node-url", help="url to connect to geth node (infura, alchemy, or private)", default=None)
    parser.add_argument("--target", help="address of the smart contract we are debugging", default=None)
    parser.add_argument("--block", help="reference block", default=None)
    parser.add_argument("--calldata", help="calldata to use for the transaction", default=None)
    parser.add_argument("--wallet", help="wallet id (as specified in ~/.config/ethtools/pwn/wallets.json )", default=None)

    args = parser.parse_args()

    ethdbg_cfg = load_ethdbg_config()

    # CHECK 1: do we have a valid chain RPC?
    if args.node_url is not None:
        # user specified a different node, let's use it first.
        try:
            w3 = get_w3_provider(args.node_url)
        except Exception:
            print(f"{RED_COLOR} ❌ Invalid node url provided: {args.node_url}{RESET_COLOR}")
            sys.exit()
    else:
        # user did not specify a node, let's use the one in the config
        try:
            w3 = get_w3_provider(ethdbg_cfg['node_url'])
        except Exception as e:
            print(f"{RED_COLOR} ❌ Invalid node url in ethdg_config: {ethdbg_cfg['node_url']}{RESET_COLOR}")
            sys.exit()

    # Get the wallet
    wallet_conf = get_wallet(w3, args.wallet)

    # Check if we support the chain
    if w3.eth.chain_id not in SUPPORTED_CHAINS:
        print(f'{RED_COLOR}Unsupported chain: [{w3.eth.chain_id}] {RESET_COLOR}')
        sys.exit(0)

    # Check if wallet and node are referring to the same chain
    if wallet_conf.network != get_chain_name(w3.eth.chain_id):
        print(f'Wallet {wallet_conf.name} is on chain {wallet_conf.network}, but node is on chain {get_chain_name(w3.eth.chain_id)}')
        sys.exit(0)

    # CHECK 2: do we have a valid sender?
    if args.sender:
        # Validate ETH address using regexp
        if not re.match(ETH_ADDRESS, args.sender):
            print(f"{RED_COLOR}Invalid ETH address provided as sender: {args.sender}{RESET_COLOR}")
            sys.exit()

    # CHECK 3: Are we re-tracing or starting a new transaction?
    if args.txid:
        # replay transaction mode
        debug_target = TransactionDebugTarget(w3)
        debug_target.replay_transaction(args.txid,
                                        sender=args.sender, to=args.target,
                                        block_number=args.block, calldata=args.calldata,
                                        full_context=args.full_context,
                                        custom_balance=args.balance)
    elif args.target:
        # interactive mode
        # is the target an address?
        if not re.match(ETH_ADDRESS, args.target):
            print(f"{RED_COLOR}Invalid ETH address provided as target: {args.target}{RESET_COLOR}")
            sys.exit()
        
        if args.value is None:
            value = 0
        else:
            value = int(args.value)
            
        debug_target = TransactionDebugTarget(w3)
        debug_target.new_transaction(to=args.target,
                                     sender=args.sender, value=value,
                                     calldata=args.calldata, block_number=args.block,
                                     wallet_conf=wallet_conf, full_context=False,
                                     custom_balance=args.balance)
    else:
        print(f"{YELLOW_COLOR}No target address or txid provided.{RESET_COLOR}")
        sys.exit()

    # Load previous sessions history.
    load_cmds_history()

    ethdbgshell = EthDbgShell(wallet_conf, w3, debug_target=debug_target, ethdbg_cfg=ethdbg_cfg)
    ethdbgshell.print_license()

    while True:
        try:
            ethdbgshell.cmdloop()
        except KeyboardInterrupt:
            print("")
            continue
        except ExitCmdException:
            print("Program terminated.")
            continue
        except RestartDbgException:
            old_breaks = ethdbgshell.breakpoints
            # If user overwritten the ethdbg config let's keep it.
            new_ethdbg_config = dict()
            for k in ethdbg_cfg.keys():
                if k == 'node_url': # skip this key
                    continue
                val = getattr(ethdbgshell, k)
                new_ethdbg_config[k] = val

            ethdbgshell = EthDbgShell(wallet_conf, w3, debug_target=debug_target,
                                        ethdbg_cfg=new_ethdbg_config, breaks=old_breaks)
            ethdbgshell.cmdqueue.append("start\n")

if __name__ == '__main__':
    main()
