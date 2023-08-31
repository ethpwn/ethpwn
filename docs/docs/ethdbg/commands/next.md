
Continues execution until the execution hits the immediately following instruction.

Unlike `step`, if the next opcode transfers the execution to another smart contract (i.e., `CALL`,`DELEGATECALL`,`STATICCALL`,`CODECALL`), the execution will continue until the next instruction of the current contract is executed (i.e., the current call instruction will be stepped over and execution breaks once it returns).

Syntax: `next`

BEFORE `next`:
![](../../imgs/next_before.png)

AFTER `next`:
![](../../imgs/next_after.png)