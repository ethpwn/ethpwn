<a id="ethtools.pwn.solidity_utils"></a>

# ethtools.pwn.solidity\_utils

<a id="ethtools.pwn.solidity_utils.decode_solidity_metadata_from_bytecode"></a>

#### decode\_solidity\_metadata\_from\_bytecode

```python
def decode_solidity_metadata_from_bytecode(bytecode)
```

Decodes the CBOR encoded solidity compiler metadata appended to the bytecode.
Should include at least the IPFS hash and the solc version, but may include
other information as well.

<a id="ethtools.pwn.solidity_utils.try_match_optimizer_settings"></a>

#### try\_match\_optimizer\_settings

```python
def try_match_optimizer_settings(compile,
                                 contract_name,
                                 bin=None,
                                 bin_runtime=None,
                                 solc_versions=None,
                                 minimize=False)
```

Tries to match the optimizer settings of the given contract to the given bytecode by repeatedly

compiling the contract with different optimizer settings until a match is found.

```
from ethtools.pwn.prelude import *

compiler = SolidityCompiler()
do_compile = functools.partial(compiler.compile_files, ['contracts/MyContract.sol'])

code = context.w3.eth.getCode('0x...')

best_kwargs, meta, result_bytecode = try_match_optimizer_settings(do_compile, 'MyContract', bin_runtime=bytecode)
print(best_kwargs)
```

**Arguments**:

- `compile`: A function that takes keyword arguments `optimizer_settings` and `solc_version`
and returns the `output_json` from the solidity compiler. This is compatible with
the `SolidityCompiler.compile_source` and `SolidityCompiler.compile_files` methods.
- `contract_name`: The name of the contract to match
- `bin`: The constructor bytecode of the contract to match or `None`
- `bin_runtime`: The runtime bytecode of the contract to match or `None`
- `solc_versions`: A list of solc versions to try, if the bytecode contains metadata
declaring the solc version, this parameter is ignored.
- `minimize`: Whether to try to minimize the number of optimizer runs or not

