# Table of Contents

* [ethtools.pwn.hashes](#ethtools.pwn.hashes)
  * [signature\_hash](#ethtools.pwn.hashes.signature_hash)
  * [register\_signature\_hash](#ethtools.pwn.hashes.register_signature_hash)
  * [lookup\_signature\_hash\_local](#ethtools.pwn.hashes.lookup_signature_hash_local)
  * [lookup\_signature\_hash\_database](#ethtools.pwn.hashes.lookup_signature_hash_database)
  * [lookup\_signature\_hash](#ethtools.pwn.hashes.lookup_signature_hash)

<a id="ethtools.pwn.hashes"></a>

# ethtools.pwn.hashes

<a id="ethtools.pwn.hashes.signature_hash"></a>

#### signature\_hash

```python
def signature_hash(plaintext)
```

Computes the signature hash of a plaintext string.

<a id="ethtools.pwn.hashes.register_signature_hash"></a>

#### register\_signature\_hash

```python
def register_signature_hash(value, hash)
```

Register a signature hash and its given pre-image (plaintext) in the global hash table.

<a id="ethtools.pwn.hashes.lookup_signature_hash_local"></a>

#### lookup\_signature\_hash\_local

```python
def lookup_signature_hash_local(hash)
```

Look up a signature hash locally in the current global hash table.

<a id="ethtools.pwn.hashes.lookup_signature_hash_database"></a>

#### lookup\_signature\_hash\_database

```python
def lookup_signature_hash_database(hash)
```

Look up a signature hash in the 4byte.directory database.

<a id="ethtools.pwn.hashes.lookup_signature_hash"></a>

#### lookup\_signature\_hash

```python
def lookup_signature_hash(hash)
```

Look up a signature hash in the global hash table. If it is not found, look it up in the
4byte.directory database and register it in the global hash table.

