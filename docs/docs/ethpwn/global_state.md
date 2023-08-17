# Global State

`ethpwn` maintains a variety of global state across runs to allow the interaction scripts to focus only on the logic of the interaction, and not on the boilerplate of setting up the environment.

Specifically, `ethpwn` maintains the following concepts in a global state: global configuration, including wallets and api keys, compiled contract metadata, and deployed contract instances.

## 📝 Configuration
The configuration for `ethpwn` is expected to be located at `~/.config/ethpwn/config.json`. This file allows you to configure a variety of settings globally, which are then used by the various modules to simplify the interaction process.

This includes the following settings:

1. `default_network`: the default network to use for all interactions
2. `default_node_urls`: default Ethereum node URLs for each network which can be used to retrieve blockchain information state
3. `wallets`: Ethereum wallets to use to interact with the different blockchain networks
4. `etherscan_api_key`: API key for etherscan, which can be used to retrieve verified source code for contracts
5. `debugger configuration`: customizations for `ethdbg`

## 🪪 ContractMetadata
`ethpwn` stores the compiled contract metadata in a global `ContractMetadata` object, which can be accessed via `CONTRACT_METADATA`.
This holds the information about every contract that was ever compiled on your machine using `ethpwn`, and can be used to retrieve the `ContractMetadata` for all of these contracts.
This allows you to simply refer to a contract by name, and `ethpwn` will automatically retrieve the correct `ContractMetadata` for you.

E.g. if you have previously compiled the code of the uniswap router contract, you can simply do `CONTRACT_METADATA['UniswapV2Router02']` to retrieve the `ContractMetadata` for this contract.

To improve this even further, `ethpwn` is also able to fetch any available verified source code for contracts from etherscan's source-code verification API if you have an API key. This allows you to transparently retrieve the metadata for these contracts without needing to explicitly compile them yourself.
To use this feature, simply set the `ETHERSCAN_API_KEY` environment variable to your etherscan API key, or add it to your `ethpwn` configuration file.

## 🌱 Contract instances
`ethpwn` also stores the addresses of all contracts that were ever deployed or interacted with using `ethpwn` in a global `ContractInstances` object, which can be accessed via `CONTRACT_INSTANCES`. Specifically, this associates the address of an instance of a contract with the `ContractMetadata` of the contract, allowing you to retrieve any metadata about it in the future via its address.

## 🐥 Tutorial

The global state allows you to write interaction scripts that only concern themselves with the logic of an interaction, without having to worry about the boilerplate of setting up the environment, compiling contracts, and associating each contract with its address.

As an example, we will use the following setup to illustrate the benefits of this design:

```bash
########## 
# install ethpwn
pip install ethpwn

# configure your ethereum node url
ethpwn config set_default_node_url --network mainnet https://mainnet.infura.io/v3/<API_KEY>

# configure your etherscan api key
ethpwn credentials add etherscan <API_KEY>

# configure your wallet in ~/.config/ethpwn/wallets.json or via the CLI
ethpwn wallets add --name my-wallet --description="My wallet" --network mainnet <ADDRESS> 0x<PRIVKEY>

# set up names for the contracts we want to use for easy access
ethpwn contract name add 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D UniswapV2Router02
ethpwn contract name add 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 WETH
ethpwn contract name add 0x6B175474E89094C44Da98b954EedeAC495271d0F DAI

########## FOR EACH CONTRACT

# fetch the verified source code for the uniswap router contract from etherscan to access its metadata and ABI
ethpwn fetch_verified_contract_at 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D
```

## Direct Interaction in `ethpwn` Scripts

Then, we can use the uniswap router contract in our scripts to interact with it.
```python
from ethpwn import *

# get the contract instance for the uniswap router contract at address 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D

MY_addr = 0x1234567890123456789012345678901234567890
deadline = int(time.time()) + 30 * 60 # 30 minutes at most

# fetch the Contract instance for the uniswap router contract
# this automatically retrieves the ABI, source code, and storage layout for the contract
uniswap_router = contract_registry().get(contract_by_name('UniswapV2Router02'))

transact(
    # this uses the automatic abi to encode the function call
    uniswap_router.w3.swapExactETHForTokens(
        100,                    # amountOutMin
        [contract_by_name('WETH'), contract_by_name('DAI')],  # path
        my_addr,                # to
        deadline                # deadline
    ),
    value=1 * ETHER
)
```

## Integration in contract deployment

Instead of performing this action manually, we can instead deploy a solidity contract to perform this action for us.
```python
from ethpwn import *

solidity_source = """
pragma solidity ^0.6.0;

interface IUniswapV2Router02 {
    function swapExactETHForTokens(uint amountOutMin, address[] calldata path, address to, uint deadline)
        external
        payable
        returns (uint[] memory amounts);
}

contract Swapper {
    IUniswapV2Router02 uniswap_router = IUniswapV2Router02(0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D);
    address WETH_addr = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address DAI_addr = 0x6B175474E89094C44Da98b954EedeAC495271d0F;
    address my_addr = 0x1234567890123456789012345678901234567890;
    uint deadline = block.timestamp + 30 * 60; // 30 minutes at most

    function getDAI(uint amountOutMin) public payable {
        uniswap_router.swapExactETHForTokens{value: msg.value}(
            amountOutMin,
            [WETH_addr, DAI_addr],
            my_addr,
            deadline
        );
    }
}
"""

# compile the contract
contract_metadata = CONTRACT_METADATA.compile_solidity_source(solidity_source, 'Swapper.sol')

# deploy the contract
contract_instance = contract_metadata.deploy()

# call the contract's `getDAI` function
txid, *_ = transact(contract_instance.w3.getDAI(100), value=1 * ETHER)
print(f"Transaction ID: {txid.hex()}")
```

## Transparent integration with `ethdbg`
Since we compiled the contract using `ethpwn`, `ethdbg` will automatically have the source-code available during a debug session.