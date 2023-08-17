<a id="ethpwn.ethlib.assembly_utils"></a>

# ethpwn.ethlib.assembly\_utils

Module containing utility functions for assembling and disassembling EVM bytecode manually
and automatically.

<a id="ethpwn.ethlib.assembly_utils.value_to_smallest_hexbytes"></a>

#### value\_to\_smallest\_hexbytes

```python
def value_to_smallest_hexbytes(value)
```

Convert an integer to the smallest possible hexbytes

<a id="ethpwn.ethlib.assembly_utils.asm_push_value"></a>

#### asm\_push\_value

```python
def asm_push_value(value)
```

Push value to the stack

<a id="ethpwn.ethlib.assembly_utils.asm_codecopy"></a>

#### asm\_codecopy

```python
def asm_codecopy(dst, src, size)
```

Copy code from src to dst

<a id="ethpwn.ethlib.assembly_utils.asm_return"></a>

#### asm\_return

```python
def asm_return(mem_offset, length)
```

Return a value from memory

<a id="ethpwn.ethlib.assembly_utils.asm_mstore"></a>

#### asm\_mstore

```python
def asm_mstore(mem_offset, value)
```

Store value at key

<a id="ethpwn.ethlib.assembly_utils.asm_mload"></a>

#### asm\_mload

```python
def asm_mload(mem_offset)
```

Load value at key

<a id="ethpwn.ethlib.assembly_utils.asm_sstore"></a>

#### asm\_sstore

```python
def asm_sstore(key, value)
```

Store value at key

<a id="ethpwn.ethlib.assembly_utils.asm_sload"></a>

#### asm\_sload

```python
def asm_sload(key)
```

Load value at key

<a id="ethpwn.ethlib.assembly_utils.create_shellcode_deployer_bin"></a>

#### create\_shellcode\_deployer\_bin

```python
def create_shellcode_deployer_bin(shellcode)
```

Create a contract that deploys shellcode at a specific address

The deployer code is as follows:
```
PUSH <len(shellcode)>   # len
PUSH <offsetof label>   # src (offset of shellcode in the deployer)
PUSH 0                  # dst-offset
CODECOPY                # copy shellcode to offset 0 from <code> + <offsetof label>

PUSH <len(shellcode)>   # length to return
PUSH 0                  # offset to return
RETURN                  # return shellcode
label:
    <shellcode goes here>
```

<a id="ethpwn.ethlib.assembly_utils.disassemble"></a>

#### disassemble

```python
def disassemble(code, start_pc=0, fork='paris')
```

Disassemble code and return a string containing the disassembly. This disassembly includes the
pc, bytes, instruction, gas cost, and description of each instruction in addition to the
standard disassembly.

<a id="ethpwn.ethlib.assembly_utils.assemble"></a>

#### assemble

```python
def assemble(code, start_pc=0, fork='paris')
```

Assemble code and return a string containing the bytecode.
code is a string such as:
    '''PUSH1 0x60
         PUSH1 0x40
         MSTORE
     '''

