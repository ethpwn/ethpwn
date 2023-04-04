#!/bin/sh


if ! command -v git >/dev/null 2>&1 ; then
    sudo apt-get install git
fi
if ! command -v python3 >/dev/null 2>&1 ; then
     sudo apt-get install python3
fi

git clone git@github.com:shellphish/ethtools.git && pip3 install -e ethtools/pwn
chmod +x ./ethtools/ethdbg/ethdbg.py

res=$(realpath ./ethtools/ethdbg/ethdbg.py)
export PATH=$res:$PATH

touch ~/.config/ethtools/wallets.json

