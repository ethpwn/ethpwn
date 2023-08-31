
Single-step. Execute the next opcode and stop.

If the next opcode transfers the execution to another smart contract (i.e., `CALL`,`DELEGATECALL`,`STATICCALL`,`CODECALL`), the next instruction you will stop at is in the target contract.

Syntax: `<step>`

BEFORE `step`:
![](../../imgs/step_before.png)

AFTER `step`:
![](../../imgs/step_after.png)