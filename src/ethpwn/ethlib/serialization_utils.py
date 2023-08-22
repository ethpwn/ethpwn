import abc
import json
from hexbytes import HexBytes
from msgpack import packb, unpackb, pack, unpack
from web3.datastructures import AttributeDict

# make json_load and json_dumps that handle AttributeDict and HexBytes serialization and deserialization transparently

SERIALIZABLE_CLASSES = []

class Serializable(abc.ABC):
    '''
    A class that can be serialized to JSON and deserialized from JSON.
    '''
    def __init_subclass__(cls) -> None:
        register_serializable(cls)
        return super().__init_subclass__()

    @abc.abstractmethod
    def to_serializable(self):
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def from_serializable(value):
        raise NotImplementedError

def register_serializable(cls):
    '''
    Register a class as serializable. This is done automatically when a class inherits from
    Serializable.
    '''
    if cls not in SERIALIZABLE_CLASSES:
        SERIALIZABLE_CLASSES.append(cls)
    return cls


def encoder_default(obj):
    if isinstance(obj, HexBytes):
        val = obj.hex()
    elif isinstance(obj, AttributeDict):
        val = dict(obj)
    elif isinstance(obj, bytes):
        val = HexBytes(obj).hex()
    elif hasattr(obj, 'to_serializable'):
        val = obj.to_serializable()
    else:
        raise TypeError(f'Object of type {type(obj)} is not JSON serializable')
    return {
        '__type__': type(obj).__name__,
        '__value__': val
    }

def decoder_object_hook(obj):
    '''
    A custom JSON decoder object_hook that can handle AttributeDict, HexBytes and Serializable objects.
    '''
    if '__type__' in obj:
        type_name = obj['__type__']
        value = obj['__value__']
        if type_name == 'HexBytes':
            return HexBytes(value)
        elif type_name == 'AttributeDict':
            return AttributeDict(value)
        else:
            for cls in SERIALIZABLE_CLASSES:
                if cls.__name__ == type_name:
                    return cls.from_serializable(value)
    return obj

def deserialize_from_file(path=None, encoding=None):
    '''
    Deserialize a file to a Python object using the custom decoder.
    '''
    if encoding is None:
        # if no encoding is specified, see if the path has a suffix and use that
        suffix = path.rsplit('.', 1)[-1]
        if suffix in ['json', 'msgpack']:
            encoding = suffix

    if encoding is None:
        encoding = 'msgpack'

    if encoding == 'json':
        with open(path, 'r') as f:
            return json.load(f, object_hook=decoder_object_hook)
    elif encoding == 'msgpack':
        with open(path, 'rb') as f:
            return unpack(f, object_hook=decoder_object_hook)
    else:
        raise ValueError(f'Unknown encoding scheme {encoding}')

def deserialize_from_bytes(s, encoding=None):
    '''
    Deserialize bytes to a Python object using the custom decoder.
    '''
    if encoding is None:
        encoding = 'msgpack'

    if encoding == 'json':
        return json.loads(s.decode(), object_hook=decoder_object_hook)
    elif encoding == 'msgpack':
        return unpackb(s, object_hook=decoder_object_hook)
    else:
        raise ValueError(f'Unknown encoding scheme {encoding}')

def serialize_to_file(obj, path, encoding=None):
    '''
    Serialize a Python object to a file using the custom encoder and a given encoding scheme.

    :param obj: the object to serialize
    :param path: the path to the file to write to (not including the suffix)
    :param encoding: the encoding scheme to use (e.g. 'json', 'msgpack')
    '''
    suffix = None
    if encoding is None:
        # if no encoding is specified, see if the path has a suffix and use that
        suffix = path.rsplit('.', 1)[-1]
        if suffix in ['json', 'msgpack']:
            encoding = suffix

    if encoding is None:
        encoding = 'msgpack' # default to the fast implementation

    if not suffix:
        path = path + '.' + encoding

    if encoding == 'json':
        with open(path, 'w') as f:
            json.dump(obj, f, default=encoder_default, indent=2)
    elif encoding == 'msgpack':
        with open(path, 'wb') as f:
            pack(obj, f, default=encoder_default)
    else:
        raise ValueError(f'Unknown encoding scheme {encoding}')

def serialize_to_bytes(obj, encoding=None):
    '''
    Serialize a Python object to a JSON string using the custom encoder.
    '''
    if encoding is None:
        encoding = 'msgpack' # default to the fast implementation

    if encoding == 'json':
        return json.dumps(obj, default=encoder_default, indent=2).encode()
    elif encoding == 'msgpack':
        return packb(obj, default=encoder_default)
    else:
        raise ValueError(f'Unknown encoding scheme {encoding}')