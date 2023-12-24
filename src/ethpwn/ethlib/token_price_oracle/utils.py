import datetime
import decimal
import typing
import web3
import eth_abi.packed
import eth_abi.abi

def solidity_keccak(abi, data) -> bytes:
    if hasattr(web3.Web3, 'solidityKeccak'):
        return web3.Web3.solidityKeccak(abi, data)
    else:
        assert hasattr(web3.Web3, 'solidity_keccak')
        return web3.Web3.solidity_keccak(abi, data)

def encode_abi(abi, data) -> bytes:
    if hasattr(eth_abi.abi, 'encode_abi'):
        return eth_abi.abi.encode_abi(abi, data)
    else:
        assert hasattr(eth_abi.abi, 'encode')
        return eth_abi.abi.encode(abi, data)

def encode_packed(abi, data) -> bytes:
    if hasattr(eth_abi.packed, 'encode_abi_packed'):
        return eth_abi.packed.encode_abi_packed(abi, data)
    else:
        assert hasattr(eth_abi.packed, 'encode_packed')
        return eth_abi.packed.encode_packed(abi, data)

def to_checksum_address(address: str) -> str:
    if hasattr(web3.Web3, 'toChecksumAddress'):
        return web3.Web3.toChecksumAddress(address)
    else:
        assert hasattr(web3.Web3, 'to_checksum_address')
        return web3.Web3.to_checksum_address(address)

def get_block_timestamp(w3: web3.Web3, block_identifier: typing.Any) -> datetime.datetime:
    block = w3.eth.get_block(block_identifier, full_transactions=False)
    dt = datetime.datetime.fromtimestamp(block['timestamp']).replace(tzinfo=datetime.timezone.utc)
    return dt

def weighted_median(pts: typing.List[typing.Tuple[int, decimal.Decimal]]) -> decimal.Decimal:
    """
    Compute a weighted median.
    
    If the weighted median lies between points (unlikely!) then we pick the higher value of the two.

    Arguments:
        pts: a List of (weight, value) tuples
    """
    assert len(pts) > 0, 'must have more than 1 point to take median, got 0'

    pts_sorted = sorted(pts, key=lambda x: x[1])

    tot_weight = sum(x for x, _ in pts_sorted)
    
    middle = tot_weight / 2

    cumsum = 0
    for weight, pt in pts_sorted:
        if cumsum + weight > middle:
            # we went too far, this point is the median!
            return pt

        cumsum += weight

    raise Exception('should be unreachable')
