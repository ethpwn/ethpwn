# Command Line Tools
`ethpwn` comes with a CLI that can be used to manage, query, and interact with the [global state](/ethpwn/ethpwn/global_state/), as well as having shortcuts to create, decode and manipulate transactions. Most components of `ethpwn` can be accessed via the CLI.

Most commands have a help page that should explain what a command will do, see for example
```bash
ethpwn -h
ethpwn wallet -h
ethpwn wallet add -h
```
This should include descriptions of the behavior of the command as well as any arguments it takes.

## 🐥 Tutorials


### Configuration Management (`ethpwn config`)
This is used to either create a new `ethpwn` configuration from scratch, or to switch across different configured chains.

```bash
ethpwn config -h
usage: ethpwn config [-h] {create,default_network,debug_transaction_errors,set_default_node_url,show} ...

Manage config for ethlib

positional arguments:
  {create,default_network,debug_transaction_errors,set_default_node_url,show}
    create              Create a new config file with a basic setup. Will interactively prompt you for the necessary information.
    default_network     Set or get the default network to use
    debug_transaction_errors
                        Set or get whether to automatically spawn an ethdbg shell if a transaction fails.
    set_default_node_url
                        Sets the default node URL for `network`.
    show                Show the current config

optional arguments:
  -h, --help            show this help message and exit

```


### Contract Metadata Management (`ethpwn contract`)

The most used command is probably `ethpwn contract`, which can be used to manage contract metadata. This metadata is stored in the `ethpwn contract_registry`, and can be used by other components of `ethpwn` to simplify interaction with contracts.

```bash
$ ethpwn contract -h
usage: ethpwn contract [-h]
                       {address,get_default_import_remappings,compile,convert_registry,deploy,register,fetch_verified_contract,decode_calldata}
                       ...

Manage contracts and their metadata

positional arguments:
  {address,get_default_import_remappings,compile,convert_registry,deploy,register,fetch_verified_contract,decode_calldata}
    address             Parse an address string into an address. The string can be in checksummed, non-
                        checksummed, or hex format.
    get_default_import_remappings
                        Print the default import remappings.
    compile             Compile a contract. Returns the contract object. Optionally, you can provide the
                        contract source code, or a list of source files to compile the contract on the
                        file.
    convert_registry    Convert the contract registry from one encoding to another. Valid encodings:
                        'json', 'msgpack'
    deploy              Deploy a contract and return the deployed contract instance.
    register            Register an instance of the contract `contract_name` at `contract_address` in the
                        contract registry. Optionally, you can provide the contract source code, or a list
                        of source files to compile the contract first.
    fetch_verified_contract
                        Fetch the verified source code for the contract at `address` from Etherscan and
                        register it in the code-registry. If the contract is not verified, an error is
                        raised. If the contract is already registered, it is returned.
    decode_calldata     Decode a transaction. Either `target_contract`+`calldata` or `tx_hash` must be
                        provided.

optional arguments:
  -h, --help            show this help message and exit


$ ethpwn contract address 0x1234...

# ONLY for testing, has no permanent effect, check to see if the contract compiles
$ ethpwn contract compile --contract_name MyContract --source_file ~/Downloads/MyContract.sol

# register a contract in the contract registry
$ ethpwn contract register MyContract 0x1234... --source_file ~/Downloads/MyContract.sol
```

### Wallet management (`ethpwn wallet`)

`ethpwn` can manage multiple wallets, and can be used to create new wallets, import existing wallets, and query the balance of wallets.

```bash
$ ethpwn wallet -h
usage: ethpwn wallet [-h] {import,add,list,balance} ...

Manage wallets for ethlib

positional arguments:
  {import,add,create,list,balance}
    import              Import wallets from a file. The file should be a JSON file with a list of wallet objects.
    add                 Add a wallet to the wallet registry.
    create              Create a new wallet and add it to the wallet registry.
    list                List the wallets in the wallet registry.
    balance             Get the balance of a wallet.

optional arguments:
  -h, --help            show this help message and exit

 # import wallets from another configuration
$ ethpwn wallet import ~/Downloads/wallets.json

# add a new wallet to the wallet registry
$ ethpwn wallet add 0xd3362F22C6d517a405b0508a045C2A8861cA3267 <private_key> --name my_wallet --description "The best wallet ever" --network sepolia

# list the wallets in the wallet registry
$ ethpwn wallet list
Wallet(address='0xd3362F22C6d517a405b0508a045C2A8861cA3267', private_key=<blinded>, name='my_wallet', description="The best wallet ever", network='sepolia')

$ ethpwn wallet balance my_wallet
Wallet my_wallet (0xd3362F22C6d517a405b0508a045C2A8861cA3267) on sepolia has 4.784452377989923737 ether (4784452377989923737 wei)
```

### Credential Management (`ethpwn credential`)

`ethpwn` can manage credentials for external services, such as Etherscan. These credentials are stored in the `ethpwn` configuration file, and can be used by other components of `ethpwn` to interact with external services.

At the moment, the only used service is Etherscan, but more can be added in the future.

```
$ ethpwn credential -h
usage: ethpwn credential [-h] {add,list,get} ...

Manage credentials for ethlib

positional arguments:
  {add,list,get}
    add           Add a credential
    list          Show credentials
    get           Get a credential

optional arguments:
  -h, --help      show this help message and exit

$ ethpwn credential add etherscan <etherscan_api_key>

$ ethpwn credential list
{'etherscan': '<etherscan_api_key>'}

$ ethpwn credential get etherscan
<etherscan_api_key>
```

### Labels (`ethpwn label`)

`ethpwn` allows you to label common ethereum addresses and contracts for convenient use in all other components of `ethpwn`. These labels are stored in the `ethpwn` configuration, and can be used to retrieve contracts from the registry. E.g. Contract addresses can be associated with multiple labels, however each label must be unique.

```
$ ethpwn label -h
usage: ethpwn label [-h] {add,get,list} ...

Manage contract labels

positional arguments:
  {add,get,list}
    add           Add a label for a contract address.
    get           Get the labels of a contract address.
    list          Show all contract labels.

optional arguments:
  -h, --help      show this help message and exit

$ ethpwn label add my_label 0x1234...

$ ethpwn label get 0x1234...
['my_label']

$ ethpwn label list
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Contract Address                           ┃ Label             ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ 0x1234...                                  │ asdf              │
└────────────────────────────────────────────┴───────────────────┘
```