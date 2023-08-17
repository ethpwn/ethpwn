# Command Line Tools

`ethpwn` comes with a CLI that can be used to manage, query, and interact with the global state, as well as having shortcuts to create, decode and manipulate transactions.

Most commands have a help page that should explain what a command will do, see for example
```bash
ethpwn -h
ethpwn wallets -h
ethpwn wallets add -h
```
This should include descriptions of the behavior of the command as well as any arguments it takes.

A current list of current valid commands is (retrieve information about each by appending `-h`):
```
ethpwn -h

ethpwn config
ethpwn config set_default_node_url
ethpwn config show

ethpwn contract
ethpwn contract address
ethpwn contract deploy
ethpwn contract register
ethpwn contract fetch_verified_source
ethpwn contract decode_calldata

ethpwn contract name
ethpwn contract name add
ethpwn contract name get
ethpwn contract name list

ethpwn wallet
ethpwn wallet add
ethpwn wallet show
ethpwn wallet import

ethpwn credential
ethpwn credential add
ethpwn credential list
ethpwn credential get

```