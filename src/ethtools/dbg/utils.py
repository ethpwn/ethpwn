
import platform
import struct

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