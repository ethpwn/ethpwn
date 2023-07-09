
import platform
import readline
import struct
import os

from pathlib import Path

RED_COLOR = "\033[31m"
GREEN_COLOR = "\033[32m"
YELLOW_COLOR = "\033[33m"
# Bright yellow
BRIGHT_YELLOW_COLOR = "\033[38;5;226m"
BLUE_COLOR = "\033[34m"
CYAN_COLOR = "\033[36m"
PURPLE_COLOR = "\033[35m"
ORANGE_COLOR = "\033[38;5;208m"
YELLOW_BACKGROUND = "\033[43m"
RED_BACKGROUND = "\033[41m"
GREEN_BACKGROUND = "\033[42m"
RESET_COLOR = "\033[0m"
HORIZONTAL_LINE  = "\u2500"
BOLD_TEXT = "\033[1m"
STRIKETHROUGH = "\u0336"

FOUR_BYTE_URL = "https://raw.githubusercontent.com/ethereum-lists/4bytes/master/signatures/{}"

# Enum for the different types of chain
# that are supported by the tool
class ChainName:
    MAINNET = 1
    SEPOLIA = 11155111

SUPPORTED_CHAINS = [ChainName.MAINNET, ChainName.SEPOLIA]

def to_snake_case(s: str) -> str:
    s = s.replace('-', '_')
    return ''.join(['_' + c.lower() if c.isupper() else c for c in s]).lstrip('_')

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

def get_chainid(chain_name):
    if chain_name == "mainnet":
        return 1
    elif chain_name == "sepolia":
        return 11155111
    else:
        raise Exception(f"Unknown chain name {chain_name}")

def get_chain_name(id):
    if id == 1:
        return "mainnet"
    elif id == 11155111:
        return "sepolia"
    else:
        raise Exception("Unknown chain id")

def load_cmds_history():
    target_folder = Path().home() / ".config" / "ethtools" / ".ethdbg_history"

    if os.path.exists(target_folder):

        # First, keep only the last 20 commands
        # (to avoid having a huge history file)
        with open(target_folder) as f:
            cmds = f.read().splitlines()
            cmds = cmds[-20:]
        # Overwrite the file
        with open(target_folder, 'w') as f:
            f.write('\n'.join(cmds))
        
        # Then, load the history!
        with open(target_folder) as f:
            cmds = f.read().splitlines()
            for cmd in cmds:
                if cmd != '':
                    readline.add_history(cmd)

def save_cmds_history(cmd):
    target_folder = Path().home() / ".config" / "ethtools" / ".ethdbg_history"
    if os.path.exists(target_folder):
        with open(target_folder, 'a') as f:
            f.write(cmd + '\n')
    else:
        with open(target_folder, 'w') as f:
            f.write(cmd + '\n')

def read_stack_int(computation, pos: int) -> int:
    """
    Read a value from the stack on the given computation, at the given position (1 = top)
    """
    val_type, val = computation._stack.values[-pos]
    if val_type == bytes:
        val = int.from_bytes(val, byteorder='big', signed=False)
    return val