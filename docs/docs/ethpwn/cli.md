# CLI

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

ethpwn wallets
ethpwn wallets add
ethpwn wallets show
ethpwn wallets import

ethpwn credentials
ethpwn credentials add
ethpwn credentials show
ethpwn credentials get

ethpwn address
ethpwn deploy
ethpwn contract_at
ethpwn fetch_verified_contract_at
ethpwn decode_calldata
```