'''
Utilities for dealing with the different units of currency in the Ethereum ecosystem.
'''

from web3 import Web3
from .global_context import context

def parse_wei(value_string):
    '''
    Parse a string representing into a wei value. The string can be in ether, gwei, or wei.
    If no unit is specified, it is assumed to be wei.
    '''
    value_string = value_string.lower()
    if value_string.strip().endswith('ether'):
        return Web3.to_wei(value_string.strip()[:-5].strip(), 'ether')
    elif value_string.strip().endswith('eth'):
        return Web3.to_wei(value_string.strip()[:-3].strip(), 'ether')
    elif value_string.strip().endswith('gwei'):
        return Web3.to_wei(value_string.strip()[:-4].strip(), 'gwei')
    else:
        return int(value_string)

# pylint: disable=redefined-outer-name
def wei(ether=None, gwei=None, wei=None):
    '''
    Convert some amount of ether, gwei, and/or wei to wei. Returns the sum of all values so you can
    do `wei(ether=1, gwei=1)` to get 1 ether and 1 gwei in wei.
    '''
    _sum = 0
    if ether is not None:
        _sum += context.w3.to_wei(ether, 'ether')
    if gwei is not None:
        _sum += context.w3.to_wei(gwei, 'gwei')
    if wei is not None:
        _sum += wei
    return _sum

def ether(wei):
    '''Convert wei to ether'''
    return context.w3.from_wei(wei, 'ether')

def gwei(wei):
    '''Convert wei to gwei'''
    return context.w3.from_wei(wei, 'gwei')
