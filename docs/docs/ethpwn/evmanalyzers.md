# EVM Analyzers

One of the coolest feature of `ethpwn` is that it makes it very easy to build custom analyses for the EVM in a customizable context.
This is accomplished through the `EVMAnalyzer` and its `Plugins`. We ship a couple of basic plugins as example, but very complicated plugins can be constructed with this methodology :)
Moreover, plugins are realized through specific hooks in the EVM, you can combine multiple plugins to implement advanced analyses!

For instance, let's say you want to collect all the SLOAD(s) done by one of the transaction with index 2 at block `12131212`, you just have to do:

```python

Script:
    from ethpwn import *
    from ethpwn.ethlib.evm.plugins.sload_tracer import SLoadTracer

    # Get EVM at block 
    a = get_evm_at_block(12131212)
    
    # Apply the first transaction in the block
    a.next_transaction()

    # Instantiate the SLOAD tracer plugin
    sload_tracer = SLoadTracer()

    # Register the plugin in the system 
    a.register_plugin(sload_tracer)
    
    # Analyze the transaction 2
    a.next_transaction()

    # Get results!
    a.plugins.sload_tracer.traced_sloads

Out:
    [TracedSLoad(id=1, slot=b'\x93\xa4\xc8\x1e\xfe\xdf\x97\xddPt\x113\xdfR\xf8\xcf.~\x0b\xc7}\xe3G\x88\xa6j\x1f\xd7\xc8\xa11\xbf', pc=1152, value=b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xd8\xd7&\xb7\x17z\x80\x00\x00'), .... ]
```