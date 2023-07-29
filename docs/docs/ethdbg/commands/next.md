move to the next OPCODE.

Differently from `step`, if the next opcode transfers the execution to another smart contract (i.e., `CALL`,`DELEGATECALL`,`STATICCALL`,`CODECALL`), the next instruction you will be the one of the current contract (i.e., the current call and all the following are gonna be step over).

Syntax: `next` 

BEFORE `next`:
![](../../imgs/next_before.png)

AFTER `next`:
![](../../imgs/next_after.png)