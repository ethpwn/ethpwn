from hexbytes import HexBytes
import requests
from sha3 import keccak_256


def signature_hash(plaintext):
    """Computes the signature hash of a plaintext string."""
    if type(plaintext) is str:
        plaintext = plaintext.encode('utf-8')
    return keccak_256(plaintext).hexdigest()[:8]

HASH_TABLE = {}
HASH_TABLE_SIGNATURES = {}

def register_signature_hash(value, hash):
    '''
    Register a signature hash and its given pre-image (plaintext) in the global hash table.
    '''
    assert signature_hash(value) == hash
    HASH_TABLE_SIGNATURES[hash] = value

def normalize_signature_hash(hash):
    return HexBytes(hash).hex()[2:]

def lookup_signature_hash_local(hash):
    '''
    Look up a signature hash locally in the current global hash table.
    '''
    hash = normalize_signature_hash(hash)
    return HASH_TABLE_SIGNATURES.get(hash, None)

def lookup_signature_hash_database(hash):
    '''
    Look up a signature hash in the 4byte.directory database.
    '''
    hash = normalize_signature_hash(hash)
    if hash == '00000000':
        return None
    # result looks like {"count":1,"next":null,"previous":null,"results":[{"id":951886,"created_at":"2023-03-24T09:22:56.366397Z","text_signature":"Revert()","hex_signature":"0xd8b98391","bytes_signature":"Ø"}]
    result = requests.get(
        f"https://www.4byte.directory/api/v1/signatures/?hex_signature=0x{hash}",
        timeout=1
    ).json()
    if result["count"] == 0:
        return None
    if result["count"] == 1:
        result = result['results'][0]
        return result["text_signature"]
    return result['results'][0]["text_signature"]

def lookup_signature_hash(hash):
    '''
    Look up a signature hash in the global hash table. If it is not found, look it up in the
    4byte.directory database and register it in the global hash table.
    '''
    hash = normalize_signature_hash(hash)
    if hash == '00000000':
        return None
    assert len(hash) == 8
    if result_local := lookup_signature_hash_local(hash):
        return result_local
    elif result_bytes4_db := lookup_signature_hash_database(hash):
        register_signature_hash(result_bytes4_db, hash)
        return result_bytes4_db
    return None