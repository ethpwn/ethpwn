<a id="ethpwn.ethlib.serialization_utils"></a>

# ethpwn.ethlib.serialization\_utils

<a id="ethpwn.ethlib.serialization_utils.Serializable"></a>

## Serializable Objects

```python
class Serializable(abc.ABC)
```

A class that can be serialized to JSON and deserialized from JSON.

<a id="ethpwn.ethlib.serialization_utils.register_serializable"></a>

#### register\_serializable

```python
def register_serializable(cls)
```

Register a class as serializable. This is done automatically when a class inherits from
Serializable.

<a id="ethpwn.ethlib.serialization_utils.decoder_object_hook"></a>

#### decoder\_object\_hook

```python
def decoder_object_hook(obj)
```

A custom JSON decoder object_hook that can handle AttributeDict, HexBytes and Serializable objects.

<a id="ethpwn.ethlib.serialization_utils.deserialize_from_file"></a>

#### deserialize\_from\_file

```python
def deserialize_from_file(path=None, encoding=None)
```

Deserialize a file to a Python object using the custom decoder.

<a id="ethpwn.ethlib.serialization_utils.deserialize_from_bytes"></a>

#### deserialize\_from\_bytes

```python
def deserialize_from_bytes(s, encoding=None)
```

Deserialize bytes to a Python object using the custom decoder.

<a id="ethpwn.ethlib.serialization_utils.serialize_to_file"></a>

#### serialize\_to\_file

```python
def serialize_to_file(obj, path, encoding=None)
```

Serialize a Python object to a file using the custom encoder and a given encoding scheme.

**Arguments**:

- `obj`: the object to serialize
- `path`: the path to the file to write to (not including the suffix)
- `encoding`: the encoding scheme to use (e.g. 'json', 'msgpack')

<a id="ethpwn.ethlib.serialization_utils.serialize_to_bytes"></a>

#### serialize\_to\_bytes

```python
def serialize_to_bytes(obj, encoding=None)
```

Serialize a Python object to a JSON string using the custom encoder.

