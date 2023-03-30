
from web3 import Web3
from .global_context import context

def parse_wei(s):
    if s.strip().endswith('ether'):
        return Web3.to_wei(s.strip()[:-5].strip(), 'ether')
    elif s.strip().endswith('gwei'):
        return Web3.to_wei(s.strip()[:-4].strip(), 'gwei')
    else:
        return int(s)

def wei(ether=None, gwei=None, wei=None):
    sum = 0
    if ether is not None:
        sum += context.w3.to_wei(ether, 'ether')
    if gwei is not None:
        sum += context.w3.to_wei(gwei, 'gwei')
    if wei is not None:
        sum += wei
    return sum

def ether(wei):
    return context.w3.from_wei(wei, 'ether')

def gwei(wei):
    return context.w3.from_wei(wei, 'gwei')