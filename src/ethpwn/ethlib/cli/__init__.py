
import argparse
import functools
import inspect
from typing import Dict, List, Callable
from rich import print as rprint

main_cli_parser = argparse.ArgumentParser()
main_cli_parser.add_argument('--silent', action='store_true', help="Don't print anything")
main_cli_subparsers = main_cli_parser.add_subparsers(dest='subcommand')
main_cli_subparsers.required = True

main_cli_handlers = {}

def parse_json(string):
    import json
    return json.loads(string)

ARG_TYPE_PARSERS = {
    str: str,
    int: lambda s: int(s, base=0),
    bool: lambda s: s.lower() in ['true', '1', 'yes'],
    List[str]: parse_json,
    Dict[str, str]: parse_json,
}
def generate_subparser_for_function(subparsers: argparse._SubParsersAction, handlers: Dict[str, Callable], function: callable):
    # extract the arguments, argument types and default values
    args = function.__code__.co_varnames[:function.__code__.co_argcount]
    # we don't support *args or **kwargs
    assert function.__code__.co_flags & (inspect.CO_VARARGS) == 0, f"unsupported function signature: *args in {function.__name__}"
    assert function.__code__.co_flags & inspect.CO_VARKEYWORDS != 0, f"must handle **kwargs in {function.__name__}"
    arg_types = function.__annotations__
    defaults = function.__defaults__ or []
    if len(defaults) > 0:
        args, kwargs = args[:-len(defaults)], args[-len(defaults):]
    else:
        args = args
        kwargs = []

    # if function.__name__ == 'set_default_node_url':


    # create the subparser
    p: argparse.ArgumentParser = subparsers.add_parser(function.__name__, help=function.__doc__.strip())
    for i, arg in enumerate(args):
        arg_type = arg_types.get(arg, str)
        arg = arg.replace('_', '-')
        p.add_argument(arg, type=ARG_TYPE_PARSERS.get(arg_type, str))
    for kwarg, default in zip(kwargs, defaults):
        arg_type = arg_types.get(kwarg, str)
        kwarg = kwarg.replace('_', '-')
        p.add_argument(f'--{kwarg}', type=ARG_TYPE_PARSERS.get(arg_type, str), default=default)

    # add the function to the handlers
    handlers[function.__name__] = function


def parser_callable(subparsers, handlers):
    return functools.partial(generate_subparser_for_function, subparsers, handlers)

def main():
    ARGS = main_cli_parser.parse_args()

    subcommand_function = main_cli_handlers[ARGS.subcommand]
    kwargs = {k.replace('-', '_'): v for k, v in vars(ARGS).items() if k not in {'subcommand', 'silent'}}
    result = subcommand_function(**kwargs)
    if result is not None and not ARGS.silent:
        rprint(result)


cmdline = parser_callable(main_cli_subparsers, main_cli_handlers)

from .config import *
from .misc import *
from .wallets import *