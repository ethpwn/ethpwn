# Table of Contents

* [ethtools.pwn.serialization\_utils](#ethtools.pwn.serialization_utils)
  * [Serializable](#ethtools.pwn.serialization_utils.Serializable)
  * [register\_serializable](#ethtools.pwn.serialization_utils.register_serializable)
  * [CustomEncoder](#ethtools.pwn.serialization_utils.CustomEncoder)
  * [custom\_decoder](#ethtools.pwn.serialization_utils.custom_decoder)
  * [deserialize\_from\_file](#ethtools.pwn.serialization_utils.deserialize_from_file)
  * [deserialize\_from\_string](#ethtools.pwn.serialization_utils.deserialize_from_string)
  * [serialize\_to\_file](#ethtools.pwn.serialization_utils.serialize_to_file)
  * [serialize\_to\_string](#ethtools.pwn.serialization_utils.serialize_to_string)

<a id="ethtools.pwn.serialization_utils"></a>

# ethtools.pwn.serialization\_utils

<a id="ethtools.pwn.serialization_utils.Serializable"></a>

## Serializable Objects

```python
class Serializable(abc.ABC)
```

A class that can be serialized to JSON and deserialized from JSON.

<a id="ethtools.pwn.serialization_utils.register_serializable"></a>

#### register\_serializable

```python
def register_serializable(cls)
```

Register a class as serializable. This is done automatically when a class inherits from
Serializable.

<a id="ethtools.pwn.serialization_utils.CustomEncoder"></a>

## CustomEncoder Objects

```python
class CustomEncoder(json.JSONEncoder)
```

A custom JSON encoder that can handle AttributeDict, HexBytes and Serializable objects.

<a id="ethtools.pwn.serialization_utils.custom_decoder"></a>

#### custom\_decoder

```python
def custom_decoder(obj)
```

A custom JSON decoder that can handle AttributeDict, HexBytes and Serializable objects.

<a id="ethtools.pwn.serialization_utils.deserialize_from_file"></a>

#### deserialize\_from\_file

```python
def deserialize_from_file(path=None)
```

Deserialize a JSON file to a Python object using the custom decoder.

<a id="ethtools.pwn.serialization_utils.deserialize_from_string"></a>

#### deserialize\_from\_string

```python
def deserialize_from_string(s)
```

Deserialize a JSON string to a Python object using the custom decoder.

<a id="ethtools.pwn.serialization_utils.serialize_to_file"></a>

#### serialize\_to\_file

```python
def serialize_to_file(obj, path)
```

Serialize a Python object to a JSON file using the custom encoder.

<a id="ethtools.pwn.serialization_utils.serialize_to_string"></a>

#### serialize\_to\_string

```python
def serialize_to_string(obj)
```

Serialize a Python object to a JSON string using the custom encoder.

