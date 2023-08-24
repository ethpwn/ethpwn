import atexit
import functools
import os
import signal
import stat
import subprocess
import sys
import tempfile
from hexbytes import HexBytes
from web3 import Web3


@functools.lru_cache(maxsize=1024)
def normalize_contract_address(address) -> str:
    """Normalize a contract address. This ensures all addresses are checksummed and have the 0x prefix."""
    if not address:
        return None

    if type(address) == str:
        address = "0x" + address.replace("0x", '').zfill(40)

    if Web3.is_checksum_address(address):
        return address

    if type(address) == int:
        address = HexBytes(address.to_bytes(20, 'big'))

    return Web3.to_checksum_address(address)


def get_shared_prefix_len(a, b):
    '''
    Get the length of the shared prefix of two strings.
    '''
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            return i
    return min(len(a), len(b))


def to_snake_case(s: str) -> str:
    '''
    Convert a string to snake case.
    '''
    s = s.replace('-', '_')
    return ''.join(['_' + c.lower() if c.isupper() else c for c in s]).lstrip('_')


def show_diff(a, b, show_old_new=False):
    '''
    Show a nice `rich` table of the diff between two objects using `deepdiff`.
    '''
    from deepdiff import DeepDiff

    from rich import print
    from rich.table import Table

    """Show a diff between two objects"""
    diff = DeepDiff(a, b, ignore_order=True)
    table = Table(title="Diff")
    table.add_column("Type")
    table.add_column("Path")
    table.add_column("Diff")

    if show_old_new:
        table.add_column("Left")
        table.add_column("Right")

    for diff_type, diff_paths in diff.items():
        for diff_path, diff_value in diff_paths.items():
            table.add_row(diff_type, diff_path, diff_value['diff'])
    print(table)


# Enum for the different types of chain
# that are supported by the tool
class ChainName:
    MAINNET = 1
    SEPOLIA = 11155111
    AVALANCHE = 43114


def get_chainid(chain_name):
    '''
    Get the chain id for a given chain name.
    '''
    if chain_name == "mainnet":
        return 1
    elif chain_name == "sepolia":
        return 11155111
    elif chain_name == "avalanche":
        return 43114
    else:
        raise Exception(f"Unknown chain name {chain_name}")


def get_chain_name(id):
    '''
    Get the chain name for a given chain id.
    '''
    if id == 1:
        return "mainnet"
    elif id == 11155111:
        return "sepolia"
    elif id == 43114:
        return "avalanche"
    else:
        raise Exception("Unknown chain id")

# thanks gallopsled/pwntools for pwnlib.util.misc, no need to reinvent the wheel
def which(name, all = False, path=None):
    """which(name, flags = os.X_OK, all = False) -> str or str set

    Works as the system command ``which``; searches $PATH for ``name`` and
    returns a full path if found.

    If `all` is :const:`True` the set of all found locations is returned, else
    the first occurrence or :const:`None` is returned.

    Arguments:
      `name` (str): The file to search for.
      `all` (bool):  Whether to return all locations where `name` was found.

    Returns:
      If `all` is :const:`True` the set of all locations where `name` was found,
      else the first location or :const:`None` if not found.

    Example:

        >>> which('sh') # doctest: +ELLIPSIS
        '.../bin/sh'
    """
    # If name is a path, do not attempt to resolve it.
    if os.path.sep in name:
        return name

    isroot = os.getuid() == 0
    out = set()
    path = path or os.environ['PATH']
    for p in path.split(os.pathsep):
        p = os.path.join(p, name)
        if os.access(p, os.X_OK):
            st = os.stat(p)
            if not stat.S_ISREG(st.st_mode):
                continue
            # work around this issue: https://bugs.python.org/issue9311
            if isroot and not \
              st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
                continue
            if all:
                out.add(p)
            else:
                return p
    if all:
        return out
    else:
        return None


def run_in_new_terminal(command, terminal=None, args=None, kill_at_exit=True, preexec_fn=None):
    """run_in_new_terminal(command, terminal=None, args=None, kill_at_exit=True, preexec_fn=None) -> int

    Run a command in a new terminal.

    When ``terminal`` is not set:
        - If ``context.terminal`` is set it will be used.
          If it is an iterable then ``context.terminal[1:]`` are default arguments.
        - If a ``pwntools-terminal`` command exists in ``$PATH``, it is used
        - If tmux is detected (by the presence of the ``$TMUX`` environment
          variable), a new pane will be opened.
        - If GNU Screen is detected (by the presence of the ``$STY`` environment
          variable), a new screen will be opened.
        - If ``$TERM_PROGRAM`` is set, that is used.
        - If X11 is detected (by the presence of the ``$DISPLAY`` environment
          variable), ``x-terminal-emulator`` is used.
        - If KDE Konsole is detected (by the presence of the ``$KONSOLE_VERSION``
          environment variable), a terminal will be split.
        - If WSL (Windows Subsystem for Linux) is detected (by the presence of
          a ``wsl.exe`` binary in the ``$PATH`` and ``/proc/sys/kernel/osrelease``
          containing ``Microsoft``), a new ``cmd.exe`` window will be opened.

    If `kill_at_exit` is :const:`True`, try to close the command/terminal when the
    current process exits. This may not work for all terminal types.

    Arguments:
        command (str): The command to run.
        terminal (str): Which terminal to use.
        args (list): Arguments to pass to the terminal
        kill_at_exit (bool): Whether to close the command/terminal on process exit.
        preexec_fn (callable): Callable to invoke before exec().

    Note:
        The command is opened with ``/dev/null`` for stdin, stdout, stderr.

    Returns:
      PID of the new terminal process
    """

    from .global_context import context
    log = context.logger

    if not terminal:
        if context.terminal:
            terminal = context.terminal[0]
            args     = context.terminal[1:]
        elif 'TMUX' in os.environ and which('tmux'):
            terminal = 'tmux'
            args     = ['splitw']
        elif 'STY' in os.environ and which('screen'):
            terminal = 'screen'
            args     = ['-t','ethpwn','bash','-c']
        # vscode sets TERM_PROGRAM, but it doesn't exist, ignore
        elif 'TERM_PROGRAM' in os.environ and os.environ['TERM_PROGRAM'] != 'vscode':
            terminal = os.environ['TERM_PROGRAM']
            args     = []
        elif 'DISPLAY' in os.environ and which('x-terminal-emulator'):
            terminal = 'x-terminal-emulator'
            args     = ['-e']
        elif 'KONSOLE_VERSION' in os.environ and which('qdbus'):
            qdbus = which('qdbus')
            window_id = os.environ['WINDOWID']
            konsole_dbus_service = os.environ['KONSOLE_DBUS_SERVICE']

            with subprocess.Popen((qdbus, konsole_dbus_service), stdout=subprocess.PIPE) as proc:
                lines = proc.communicate()[0].decode().split('\n')

            # Iterate over all MainWindows
            for line in lines:
                parts = line.split('/')
                if len(parts) == 3 and parts[2].startswith('MainWindow_'):
                    name = parts[2]
                    with subprocess.Popen((qdbus, konsole_dbus_service, '/konsole/' + name,
                                           'org.kde.KMainWindow.winId'), stdout=subprocess.PIPE) as proc:
                        target_window_id = proc.communicate()[0].decode().strip()
                        if target_window_id == window_id:
                            break
            else:
                log.error('MainWindow not found')

            # Split
            subprocess.run((qdbus, konsole_dbus_service, '/konsole/' + name,
                            'org.kde.KMainWindow.activateAction', 'split-view-left-right'), stdout=subprocess.DEVNULL)

            # Find new session
            with subprocess.Popen((qdbus, konsole_dbus_service, os.environ['KONSOLE_DBUS_WINDOW'],
                                   'org.kde.konsole.Window.sessionList'), stdout=subprocess.PIPE) as proc:
                session_list = map(int, proc.communicate()[0].decode().split())
            last_konsole_session = max(session_list)

            terminal = 'qdbus'
            args = [konsole_dbus_service, '/Sessions/{}'.format(last_konsole_session),
                    'org.kde.konsole.Session.runCommand']

        else:
            is_wsl = False
            if os.path.exists('/proc/sys/kernel/osrelease'):
                with open('/proc/sys/kernel/osrelease', 'rb') as f:
                    is_wsl = b'icrosoft' in f.read()
            if is_wsl and which('cmd.exe') and which('wsl.exe') and which('bash.exe'):
                terminal    = 'cmd.exe'
                args        = ['/c', 'start']
                distro_name = os.getenv('WSL_DISTRO_NAME')

                # Split pane in Windows Terminal
                if 'WT_SESSION' in os.environ and which('wt.exe'):
                    args.extend(['wt.exe', '-w', '0', 'split-pane', '-d', '.'])

                if distro_name:
                    args.extend(['wsl.exe', '-d', distro_name, 'bash', '-c'])
                else:
                    args.extend(['bash.exe', '-c'])


    if not terminal:
        log.error('Could not find a terminal binary to use. Set context.terminal to your terminal.')
    elif not which(terminal):
        log.error('Could not find terminal binary %r. Set context.terminal to your terminal.' % terminal)

    if isinstance(args, tuple):
        args = list(args)

    # When not specifying context.terminal explicitly, we used to set these flags above.
    # However, if specifying terminal=['tmux', 'splitw', '-h'], we would be lacking these flags.
    # Instead, set them here and hope for the best.
    if terminal == 'tmux':
        args += ['-F' '#{pane_pid}', '-P']

    argv = [which(terminal)] + args

    if isinstance(command, str):
        if ';' in command:
            log.error("Cannot use commands with semicolon.  Create a script and invoke that directly.")
        argv += [command]
    elif isinstance(command, (list, tuple)):
        # Dump the full command line to a temporary file so we can be sure that
        # it is parsed correctly, and we do not need to account for shell expansion
        script = '''
#!{executable!s}
import os
os.execve({argv0!r}, {argv!r}, os.environ)
'''
        script = script.format(executable=sys.executable,
                               argv=command,
                               argv0=which(command[0]))
        script = script.lstrip()

        log.debug("Created script for new terminal:\n%s" % script)

        with tempfile.NamedTemporaryFile(delete=False, mode='wt+') as tmp:
          tmp.write(script)
          tmp.flush()
          os.chmod(tmp.name, 0o700)
          argv += [tmp.name]


    log.debug("Launching a new terminal: %r" % argv)

    stdin = stdout = stderr = open(os.devnull, 'r+b')
    if terminal == 'tmux':
        stdout = subprocess.PIPE

    p = subprocess.Popen(argv, stdin=stdin, stdout=stdout, stderr=stderr, preexec_fn=preexec_fn)

    if terminal == 'tmux':
        out, _ = p.communicate()
        pid = int(out)
    elif terminal == 'qdbus':
        with subprocess.Popen((qdbus, konsole_dbus_service, '/Sessions/{}'.format(last_konsole_session),
                               'org.kde.konsole.Session.processId'), stdout=subprocess.PIPE) as proc:
            pid = int(proc.communicate()[0].decode())
    else:
        pid = p.pid

    if kill_at_exit:
        def kill():
            try:
                if terminal == 'qdbus':
                    os.kill(pid, signal.SIGHUP)
                else:
                    os.kill(pid, signal.SIGTERM)
            except OSError:
                pass

        atexit.register(kill)

    return pid