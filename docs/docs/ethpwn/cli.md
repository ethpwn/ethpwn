# Command Line Tools

`ethpwn` comes with a CLI that can be used to manage, query, and interact with the global state, as well as having shortcuts to create, decode and manipulate transactions. Most components of `ethpwn` can be accessed via the CLI.

Most commands have a help page that should explain what a command will do, see for example
```bash
ethpwn -h
ethpwn wallets -h
ethpwn wallets add -h
```
This should include descriptions of the behavior of the command as well as any arguments it takes.


### Contract Metadata Management (`ethpwn contract`)

The most used command is probably `ethpwn contract`, which can be used to manage contract metadata. This metadata is stored in the `ethpwn contract_registry`, and can be used by other components of `ethpwn` to simplify interaction with contracts.

```bash
$ ethpwn contract -h
usage: ethpwn contract [-h]
                       {address,deploy,get_default_import_remappings,compile,convert_registry,register,fetch_verified_contract_source,decode_calldata,name} ...
```

### Wallet management (`ethpwn wallet`)

`ethpwn` can manage multiple wallets, and can be used to create new wallets, import existing wallets, and query the balance of wallets.

```bash
$ ethpwn wallet -h
usage: ethpwn wallet [-h] {import,add,list,balance} ...

Manage wallets for ethlib

positional arguments:
  {import,add,list,balance}
    import              Import wallets from a file. The file should be a JSON file with a list of wallet objects.
    add                 Add a wallet to the wallet registry.
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

$ ethpwn wallet my_wallet ethernaut
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