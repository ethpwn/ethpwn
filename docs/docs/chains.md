
`ethpwn` currently has a backend that can only support EVM-based chains.

Currently we support the following ones:

| Chain Name | Chain Id | Supported |
|-------------------|----------|----------|
| GREEDY_SHA  | False | ✅ |
| LAZY_SOLVES | False | ✅ |



    options.GREEDY_SHA = True
    options.LAZY_SOLVES = False
    options.STATE_INSPECT = False
    options.MAX_SHA_SIZE = 300
    options.OPTIMISTIC_CALL_RESULTS = True
    options.DEFAULT_EXTCODESIZE = True
    options.DEFAULT_CREATE2_RESULT_ADDRESS = True
    options.DEFAULT_CREATE_RESULT_ADDRESS = True
    options.MATH_CONCRETIZE_SYMBOLIC_EXP_EXP = True
    options.MATH_CONCRETIZE_SYMBOLIC_EXP_BASE = True