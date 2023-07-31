
import json
import platform
import readline
import struct
import os

from pathlib import Path
from ..ethlib.utils import ChainName

RED_COLOR = "\033[31m"
GREEN_COLOR = "\033[32m"
YELLOW_COLOR = "\033[33m"
# Bright yellow
BRIGHT_YELLOW_COLOR = "\033[38;5;226m"
BLUE_COLOR = "\033[34m"
CYAN_COLOR = "\033[36m"
PURPLE_COLOR = "\033[35m"
ORANGE_COLOR = "\033[38;5;208m"
# Purple
PURPLE_COLOR = "\033[38;5;141m"
YELLOW_BACKGROUND = "\033[43m"
RED_BACKGROUND = "\033[41m"
GREEN_BACKGROUND = "\033[42m"
RESET_COLOR = "\033[0m"
HORIZONTAL_LINE  = "\u2500"
BOLD_TEXT = "\033[1m"
STRIKETHROUGH = "\u0336"

FOUR_BYTE_URL = "https://raw.githubusercontent.com/ethereum-lists/4bytes/master/signatures/{}"


SUPPORTED_CHAINS = [ChainName.MAINNET, ChainName.SEPOLIA]

def get_terminal_size():
    """Return the current terminal size."""
    if platform.system() == "Windows":
        from ctypes import windll, create_string_buffer
        hStdErr = -12
        herr = windll.kernel32.GetStdHandle(hStdErr)
        csbi = create_string_buffer(22)
        res = windll.kernel32.GetConsoleScreenBufferInfo(herr, csbi)
        if res:
            _, _, _, _, _, left, top, right, bottom, _, _ = struct.unpack("hhhhHhhhhhh", csbi.raw)
            tty_columns = right - left + 1
            tty_rows = bottom - top + 1
            return tty_rows, tty_columns
        else:
            return 600, 100
    else:
        import fcntl
        import termios
        try:
            tty_rows, tty_columns = struct.unpack("hh", fcntl.ioctl(1, termios.TIOCGWINSZ, "1234"))
            return tty_rows, tty_columns
        except OSError:
            return 600, 100

def load_cmds_history():
    target_file = Path().home() / ".config" / "ethpwn" / ".ethdbg_history"

    if os.path.exists(target_file):

        # First, keep only the last 100 unique commands
        # (to avoid having a huge history file)
        with open(target_file) as f:
            cmds = f.read().splitlines()
            cmds = cmds[-100:]

        unique_cmds = []
        for cmd in cmds:
            if cmd not in unique_cmds:
                unique_cmds.append(cmd)

        # Overwrite the file
        with open(target_file, 'w') as f:
            f.write('\n'.join(unique_cmds))

        # Then, load the history!
        with open(target_file) as f:
            cmds = f.read().splitlines()
            for cmd in cmds:
                cmd = cmd.strip()
                if cmd != '':
                    readline.add_history(cmd)

def save_cmds_history(cmd):
    target_file = Path().home() / ".config" / "ethpwn" / ".ethdbg_history"
    if os.path.exists(target_file):
        with open(target_file, 'a') as f:
            f.write('\n'+cmd +'\n')
    else:
        with open(target_file, 'w') as f:
            f.write('\n'+cmd + '\n')

def load_ethdbg_config():
    target_file = Path().home() / ".config" / "ethpwn" / "ethdbg_config"
    if os.path.exists(target_file):
        with open(target_file) as f:
            return json.load(f)
    else:
        # create an empty config file
        # with default values
        with open(target_file, 'w') as f:
            json.dump({
                "node_url": "<PLEASE-SET-THIS-VALUE>",
            }, f)
        with open(target_file) as f:
            return json.load(f)

def read_stack_int(computation, pos: int) -> int:
    """
    Read a value from the stack on the given computation, at the given position (1 = top)
    """
    val_type, val = computation._stack.values[-pos]
    if val_type == bytes:
        val = int.from_bytes(val, byteorder='big', signed=False)
    return val

def read_stack_bytes(computation, pos: int) -> int:
    """
    Read a value from the stack on the given computation, at the given position (1 = top)
    """
    _, val = computation._stack.values[-pos]
    return val


def calculate_create_contract_address(w3, sender_address, nonce):
    assert(False)


def calculate_create2_contract_address(w3, sender_address, salt, init_code_bytes):
    # Convert the sender address to bytes
    pre = '0xff'
    arg1 = bytes.fromhex(pre[2:])
    arg2 = sender_address
    arg3 = salt
    arg4 = init_code_bytes

    keccak_b_code = w3.keccak(arg4)
    b_result = w3.keccak(arg1+arg2+arg3+keccak_b_code)
    contract_address = w3.to_checksum_address(b_result[12:].hex())
    return contract_address