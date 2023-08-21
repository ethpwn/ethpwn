
import argparse
import functools
import inspect
import sys
from typing import Dict, List, Callable
from rich import print as rprint

main_cli_parser = argparse.ArgumentParser()
main_cli_parser.add_argument('--silent', action='store_true', help="Don't print anything")
main_cli_subparsers = main_cli_parser.add_subparsers(dest='subcommand')
main_cli_subparsers.required = True

main_cli_handlers = {}

# inspired by https://gist.github.com/vadimkantorov/37518ff88808af840884355c845049ea
class ParseKVAction(argparse.Action):
    def __init__(self, key_type, value_type, *args, **kwargs):
        self.key_type = key_type
        self.value_type = value_type
        super().__init__(*args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest, None) is None:
            setattr(namespace, self.dest, dict())

        if type(values) is str:
            values = values.split(';')

        for each in values:
            try:
                key, value = each.split("=", 1)
                key = self.key_type(key)
                value = self.value_type(value)
                getattr(namespace, self.dest)[key] = value
            except ValueError as ex:
                message = "\nTraceback: {}".format(ex)
                message += "\nError on '{}' || It should be 'key=value'".format(each)
                raise argparse.ArgumentError(self, str(message))

def parse_json(string):
    import json
    return json.loads(string)

PRIMITIVE_TYPE_PARSERS = {
    str: str,
    int: lambda s: int(s, base=0),
    bool: lambda s: s.lower() in ['true', '1', 'yes'],
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

def add_parser_arg(parser, name, type, default=None, help=None):
    if type in PRIMITIVE_TYPE_PARSERS:
        parser.add_argument(name, type=PRIMITIVE_TYPE_PARSERS[type], default=default, help=help)

    # check if it's a typing value and it has a __origin__
    elif hasattr(type, '__origin__'):
        # check if it's typing.List
        if type.__origin__ is list:
            inner_type = type.__args__[0]
            assert inner_type in PRIMITIVE_TYPE_PARSERS, f"unsupported type {type} for argument {name}"
            assert default is None or isinstance(default, list), f"invalid default value {default} for argument {name}"
            default = default or list()
            parser.add_argument(name, type=PRIMITIVE_TYPE_PARSERS[inner_type], action='append', help=help, default=default)

        # check if it's typing.Dict
        elif type.__origin__ is dict:
            key_type, value_type = type.__args__
            assert key_type in PRIMITIVE_TYPE_PARSERS, f"unsupported type {type} for argument {name}"
            assert value_type in PRIMITIVE_TYPE_PARSERS, f"unsupported type {type} for argument {name}"
            assert default is None or isinstance(default, dict), f"invalid default value {default} for argument {name}"
            default = default or dict()
            parser.add_argument(
                name,
                action=ParseKVAction,
                help=help,
                default=default,
                key_type=key_type,
                value_type=value_type
            )

        else:
            raise Exception(f"unsupported type {type} for argument {name}")

    else:
        parser.add_argument(name, type=type, help=help, default=default)

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

    if fname == 'compile':
        import ipdb; ipdb.set_trace()

    # create the subparser
    try:
        short_help, _ = function_doc.split('\n\n', maxsplit=1)
    except ValueError:
        short_help = function_doc
    p: argparse.ArgumentParser = subparsers.add_parser(fname, description=function_doc, help=short_help)

    for i, arg in enumerate(args):
        arg_type = arg_types.get(arg, str)
        arg = arg.replace('_', '-')
        add_parser_arg(p, arg, arg_type, param_docs.get(arg, None))

    for kwarg, default in zip(kwargs, defaults):
        arg_type = arg_types.get(kwarg, str)
        kwarg = kwarg.replace('_', '-')
        add_parser_arg(p, f"--{kwarg}", arg_type, default, param_docs.get(kwarg, None))

    function.__cli_parser__ = p

    # add the function to the handlers
    handlers[fname] = function
    return function


def parser_callable(subparsers, handlers):
    return functools.partial(generate_subparser_for_function, subparsers, handlers)


def subcommand_callable(super_callable, __subcommand_name, __subcommand_doc=''):
    handlers = {}

    def __handler(__subcommand_name, __subcommand_handlers, **kwargs):
        subcommand = kwargs.pop('subcommand_' + __subcommand_name)
        return __subcommand_handlers[subcommand](**kwargs)

    __handler.__name__ = __subcommand_name
    __handler.__doc__ = __subcommand_doc

    # bind handlers to the handler
    __handler = functools.partial(__handler, __subcommand_name, handlers)

    __handler = super_callable(__handler)

    subparsers = __handler.__cli_parser__.add_subparsers(dest='subcommand_' + __subcommand_name)
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


def main(args=None):
    args = args or sys.argv[1:]
    try:
        import ipdb; ipdb.set_trace()
        ARGS = main_cli_parser.parse_args(args=args)
    except Exception as e:
        main_cli_parser.print_help()
        return

    subcommand_function = main_cli_handlers[ARGS.subcommand]
    kwargs = {k.replace('-', '_'): v for k, v in vars(ARGS).items() if k not in {'subcommand', 'silent'}}

    result = subcommand_function(**kwargs)
    if result is not None and not ARGS.silent:
        rprint(result)


cmdline = parser_callable(main_cli_subparsers, main_cli_handlers)

from .config import *
from .contract import *
from .wallet import *
from .credential import *