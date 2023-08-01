
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
def parse_doc(doc: str):
    param_docs = {}
    return_doc = None
    real_doc = ''

    for line in doc.split('\n'):
        line = line.strip()
        if line.startswith(':param'):
            line = line[6:].strip()
            param_name, param_doc = line.split(':', maxsplit=1)
            param_docs[param_name.strip()] = param_doc.strip()
        elif line.startswith(':return:'):
            line = line[8:].strip()
            return_doc = line.strip()
        else:
            real_doc += line + '\n'

    return param_docs, return_doc, real_doc.strip()

def generate_subparser_for_function(subparsers: argparse._SubParsersAction, handlers: Dict[str, Callable], function: callable):
    if type(function) is functools.partial:
        # code = function.func.__code__
        fname = function.func.__name__
        argcount = function.func.__code__.co_argcount
        varnames = function.func.__code__.co_varnames[:argcount][len(function.args):]
        code_flags = function.func.__code__.co_flags
        annotations = function.func.__annotations__
        defaults = function.func.__defaults__ # strip the partial'ed args
        func_doc = function.func.__doc__
    else:
        # code = function.__code__
        fname = function.__name__
        argcount = function.__code__.co_argcount
        varnames = function.__code__.co_varnames[:argcount]
        code_flags = function.__code__.co_flags
        annotations = function.__annotations__
        defaults = function.__defaults__
        func_doc = function.__doc__

    args = varnames
    # we don't support *args or **kwargs
    assert code_flags & (inspect.CO_VARARGS) == 0, f"unsupported function signature: *args in {fname}"
    assert code_flags & inspect.CO_VARKEYWORDS != 0, f"must handle **kwargs in {fname}"
    arg_types = annotations
    defaults = defaults or []
    if len(defaults) > 0:
        args, kwargs = args[:-len(defaults)], args[-len(defaults):]
    else:
        args = args
        kwargs = []

    param_docs, return_doc, function_doc = parse_doc(func_doc)

    # create the subparser
    p: argparse.ArgumentParser = subparsers.add_parser(fname, help=function_doc)
    for i, arg in enumerate(args):
        arg_type = arg_types.get(arg, str)
        arg = arg.replace('_', '-')
        p.add_argument(arg, type=ARG_TYPE_PARSERS.get(arg_type, str), help=param_docs.get(arg, None))
    for kwarg, default in zip(kwargs, defaults):
        arg_type = arg_types.get(kwarg, str)
        kwarg = kwarg.replace('_', '-')
        p.add_argument(f'--{kwarg}', type=ARG_TYPE_PARSERS.get(arg_type, str), default=default, help=param_docs.get(kwarg, None))

    function.__cli_parser__ = p

    # add the function to the handlers
    handlers[fname] = function
    return function


def parser_callable(subparsers, handlers):
    return functools.partial(generate_subparser_for_function, subparsers, handlers)


def subcommand_callable(super_callable, name, doc=''):
    handlers = {}

    def __handler(name, handlers, **kwargs):
        subcommand = kwargs.pop('subcommand_' + name)
        return handlers[subcommand](**kwargs)

    __handler.__name__ = name
    __handler.__doc__ = doc

    # bind handlers to the handler
    __handler = functools.partial(__handler, name, handlers)

    __handler = super_callable(__handler)

    subparsers = __handler.__cli_parser__.add_subparsers(dest='subcommand_' + name)
    __handler.__cli_subparsers__ = subparsers
    __handler.__cli_handlers__ = handlers
    __handler.__cli_parser_callable__ = parser_callable(subparsers, handlers)
    __handler.__cli_parser_callable__.__cli_parent__handler = __handler
    return __handler.__cli_parser_callable__

def rename(new_name):
    def decorator(f):
        f.__name__ = new_name
        return f
    return decorator


def main():
    ARGS = main_cli_parser.parse_args()
    import ipdb; ipdb.set_trace()
    subcommand_function = main_cli_handlers[ARGS.subcommand]
    kwargs = {k.replace('-', '_'): v for k, v in vars(ARGS).items() if k not in {'subcommand', 'silent'}}
    result = subcommand_function(**kwargs)
    if result is not None and not ARGS.silent:
        rprint(result)


cmdline = parser_callable(main_cli_subparsers, main_cli_handlers)

from .config import *
from .contracts import *
from .wallets import *
from .credentials import *