import abc
import json
from hexbytes import HexBytes

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


class CustomEncoder(json.JSONEncoder):
    '''
    A custom JSON encoder that can handle AttributeDict, HexBytes and Serializable objects.
    '''
    def default(self, obj):
        if isinstance(obj, HexBytes):
            val = obj.hex()
        elif isinstance(obj, AttributeDict):
            val = dict(obj)
        elif hasattr(obj, 'to_serializable'):
            val = obj.to_serializable()
        else:
            val = json.JSONEncoder.default(self, obj)
        return {
            '__type__': type(obj).__name__,
            '__value__': val
        }

def custom_decoder(obj):
    '''
    A custom JSON decoder that can handle AttributeDict, HexBytes and Serializable objects.
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

def deserialize_from_file(path=None):
    '''
    Deserialize a JSON file to a Python object using the custom decoder.
    '''
    with open(path, 'r') as f:
        return json.load(f, object_hook=custom_decoder)

def deserialize_from_string(s):
    '''
    Deserialize a JSON string to a Python object using the custom decoder.
    '''
    return json.loads(s, object_hook=custom_decoder)

def serialize_to_file(obj, path):
    '''
    Serialize a Python object to a JSON file using the custom encoder.
    '''
    serialized = serialize_to_string(obj)
    with open(path, 'w') as f:
        f.write(serialized)

def serialize_to_string(obj):
    '''
    Serialize a Python object to a JSON string using the custom encoder.
    '''
    return json.dumps(obj, cls=CustomEncoder)