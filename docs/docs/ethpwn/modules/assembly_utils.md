<a id="ethtools.pwn.assembly_utils"></a>

# ethtools.pwn.assembly\_utils

Module containing utility functions for assembling and disassembling EVM bytecode manually
and automatically.

<a id="ethtools.pwn.assembly_utils.value_to_smallest_hexbytes"></a>

#### value\_to\_smallest\_hexbytes

```python
def value_to_smallest_hexbytes(value)
```

Convert an integer to the smallest possible hexbytes

<a id="ethtools.pwn.assembly_utils.asm_push_value"></a>

#### asm\_push\_value

```python
def asm_push_value(value)
```

Push value to the stack

<a id="ethtools.pwn.assembly_utils.asm_codecopy"></a>

#### asm\_codecopy

```python
def asm_codecopy(dst, src, size)
```

Copy code from src to dst

<a id="ethtools.pwn.assembly_utils.asm_return"></a>

#### asm\_return

```python
def asm_return(mem_offset, length)
```

Return a value from memory

<a id="ethtools.pwn.assembly_utils.asm_mstore"></a>

#### asm\_mstore

```python
def asm_mstore(mem_offset, value)
```

Store value at key

<a id="ethtools.pwn.assembly_utils.asm_mload"></a>

#### asm\_mload

```python
def asm_mload(mem_offset)
```

Load value at key

<a id="ethtools.pwn.assembly_utils.asm_sstore"></a>

#### asm\_sstore

```python
def asm_sstore(key, value)
```

Store value at key

<a id="ethtools.pwn.assembly_utils.asm_sload"></a>

#### asm\_sload

```python
def asm_sload(key)
```

Load value at key

<a id="ethtools.pwn.assembly_utils.create_shellcode_deployer_bin"></a>

#### create\_shellcode\_deployer\_bin

```python
def create_shellcode_deployer_bin(shellcode)
```

Create a contract that deploys shellcode at a specific address

<a id="ethtools.pwn.assembly_utils.disassemble_pro"></a>

#### disassemble\_pro

```python
def disassemble_pro(code, start_pc=0, fork='paris')
```

Disassemble code and return a string containing the disassembly. This disassembly includes the
pc, bytes, instruction, gas cost, and description of each instruction in addition to the
standard disassembly.