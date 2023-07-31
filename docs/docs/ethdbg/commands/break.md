The command `break` works similarly to a GDB breakpoint.

A breakpoint in `ethdbg` can be `simple` or `conditional`.

#### 💥 Simple Breakpoint
A simple breakpoint can be placed on a specific value of the `<PC>` or at a specific `<OPCODE>`

Syntax: 

 + `break <PC>`
 + `break <OPCODE>` 

![](../../imgs/simple_break_pc.png)
![](../../imgs/simple_break_op.png)

| ❗️ Note                               | 
|------------------------------------------|
| Make sure the chosen OPCODE is available in the EVM version currently executing the transaction. |

#### 💥 Conditional Breakpoint

The expresiveness of a conditional breakpoint is currently quite limited, but they already support some interesting combination of events.

A conditional breakpoint is set by specifying a tuple of the form `<what><when><value>`.
Multiple `<what><when><value>` tuples create more complex stop conditions that are joined together in AND.

Syntax:  `break <what><when><value>,<what><when><value>,...`

Currently we support the following `<what>` and `<when>`:

| What | Description |
|-------------------|----------|
|`pc`    | specify the value of the PC                                    |
|`op`    | specify the OPCODE at which you want to stop                   |   
|`addr`  | specify what is the value of the code address executing        | 
|`saddr` | specify what is the value of the storage address executing     | 
|`value` | stop when a particular amount of ETH is sent as part of a CALL | 
|`gas_remaining` | stop when a specific value of gas is remaining         |

| ❗️ Note                               | 
|------------------------------------------|
| Note how `addr` and `saddr` represent different addresses. `addr` is the code address, i.e., the address of the smart contract currently executing. On the other hand, `saddr` is the storage address, i.e., the address of the contract whose storage will be modified when storage operations occurr (see DELEGATECALL) |

| When | Description |
|-------------------|----------|
|`[= or ==]`  |  Equality                           |
| `!=`        |  NOT equality                       |
|`[> or >=]`  |  Greater than/Greater or Equal then |
|`[< or <=]`  |  Lower than/Lower or Equal then     |

For instance, one can set a breakpoint only when the OPCODE is an `SSTORE` that operates on the storage of a specific contract address by doing: 

```
break op=SSTORE,saddr=0x5a51E2ebF8D136926b9cA7b59B60464E7C44d2Eb
```

![](../../imgs/conditional_break_ex1.png)