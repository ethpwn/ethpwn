import json
from hexbytes import HexBytes

from web3.datastructures import AttributeDict

# make json_load and json_dumps that handle AttributeDict and HexBytes serialization and deserialization transparently

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, HexBytes):
            return obj.hex()
        if isinstance(obj, AttributeDict):
             return dict(obj)
        return json.JSONEncoder.default(self, obj)

def json_load(f):
    return json.load(f, object_hook=AttributeDict)

def json_loads(s):
    return json.loads(s, object_hook=AttributeDict)

def json_dump(obj, f):
    json.dump(obj, f, cls=CustomEncoder)

def json_dumps(obj):
    return json.dumps(obj, cls=CustomEncoder)