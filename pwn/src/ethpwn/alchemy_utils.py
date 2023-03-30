from hexbytes import HexBytes
from .global_context import context
from .contract_registry import CONTRACT_METADATA, decode_function_input

def decode_simulation_trace(trace):
    """
    Decode the simulation trace, and return a prettified list of the calls made
    """
    for call in trace.calls:
        dest = call.to
        input = call.input
        decoded = decode_function_input(dest, input, guess=True)
        if decoded:
            call.input = decoded
    return trace

def pretty_print_simulation_trace(trace):
    """
    Pretty print the simulation trace
    """
    for call in trace.calls:
        src = HexBytes(call['from'])
        dest = HexBytes(call.to)
        input = HexBytes(call.input)
        output = HexBytes(call.output)
        value = call.get('value', 0)
        gasUsed = call.gasUsed
        decoded = decode_function_input(dest, input, guess=True)
        # import ipdb; ipdb.set_trace()
        if decoded is not None:
            metadata, function, args = decoded
            # import ipdb; ipdb.set_trace()
            contract_name = 'UNKNOWN' if metadata is None else metadata.contract_name
            decoded = f"{contract_name}:{function} [{', '.join(map(repr, args))}]"

        decoded_output = decode_function_input(dest, output, guess=True)
        if decoded_output is not None:
            metadata, function, args = decoded_output
            contract_name = 'UNKNOWN' if metadata is None else metadata.contract_name
            decoded_output = f"{contract_name}:{function} [{', '.join(map(repr, args))}]"

        msg = f"{src.hex()} -> {dest.hex()} gas={gasUsed}) ({value} ETH)\nINPUT: {decoded} {input.hex()=}\nOUTPUT: {decoded_output} {output.hex()=}\n"
        print(msg)



def simulate_execution(transaction_data):
    """
    Simulate the execution of a transaction, and return the trace
    """
    return context.w3.manager.request_blocking('alchemy_simulateExecution', transaction_data)