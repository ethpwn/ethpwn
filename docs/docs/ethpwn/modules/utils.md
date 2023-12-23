<a id="ethpwn.ethlib.utils"></a>

# ethpwn.ethlib.utils

<a id="ethpwn.ethlib.utils.normalize_contract_address"></a>

#### normalize\_contract\_address

```python
@functools.lru_cache(maxsize=1024)
def normalize_contract_address(address_or_label, resolve_labels=True) -> str
```

Normalize a contract address. This ensures all addresses are checksummed and have the 0x prefix.

<a id="ethpwn.ethlib.utils.get_shared_prefix_len"></a>

#### get\_shared\_prefix\_len

```python
def get_shared_prefix_len(a, b)
```

Get the length of the shared prefix of two strings.

<a id="ethpwn.ethlib.utils.to_snake_case"></a>

#### to\_snake\_case

```python
def to_snake_case(s: str) -> str
```

Convert a string to snake case.

<a id="ethpwn.ethlib.utils.show_diff"></a>

#### show\_diff

```python
def show_diff(a, b, show_old_new=False)
```

Show a nice `rich` table of the diff between two objects using `deepdiff`.

<a id="ethpwn.ethlib.utils.get_chainid"></a>

#### get\_chainid

```python
def get_chainid(chain_name)
```

Get the chain id for a given chain name.

<a id="ethpwn.ethlib.utils.get_chain_name"></a>

#### get\_chain\_name

```python
def get_chain_name(id)
```

Get the chain name for a given chain id.

<a id="ethpwn.ethlib.utils.which"></a>

#### which

```python
def which(name, all=False, path=None)
```

which(name, flags = os.X_OK, all = False) -> str or str set

Works as the system command ``which``; searches $PATH for ``name`` and
returns a full path if found.

If `all` is :const:`True` the set of all found locations is returned, else
the first occurrence or :const:`None` is returned.

**Arguments**:

- ``name`` _str_ - The file to search for.
- ``all`` _bool_ - Whether to return all locations where `name` was found.
  

**Returns**:

  If `all` is :const:`True` the set of all locations where `name` was found,
  else the first location or :const:`None` if not found.
  

**Example**:

  
  >>> which('sh') # doctest: +ELLIPSIS
  '.../bin/sh'

<a id="ethpwn.ethlib.utils.run_in_new_terminal"></a>

#### run\_in\_new\_terminal

```python
def run_in_new_terminal(command,
                        terminal=None,
                        args=None,
                        kill_at_exit=True,
                        preexec_fn=None)
```

run_in_new_terminal(command, terminal=None, args=None, kill_at_exit=True, preexec_fn=None) -> int

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

**Arguments**:

- `command` _str_ - The command to run.
- `terminal` _str_ - Which terminal to use.
- `args` _list_ - Arguments to pass to the terminal
- `kill_at_exit` _bool_ - Whether to close the command/terminal on process exit.
- `preexec_fn` _callable_ - Callable to invoke before exec().
  

**Notes**:

  The command is opened with ``/dev/null`` for stdin, stdout, stderr.
  

**Returns**:

  PID of the new terminal process

