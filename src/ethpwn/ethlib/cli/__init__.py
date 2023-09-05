
import argparse
import functools
import inspect
import sys
from typing import Dict, List, Callable
from rich import print as rprint

from ..python_introspection_utils import extract_fully_annotated_args, parse_doc

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

def parser_arg_type_keys(name, type, default=None):
    if type in PRIMITIVE_TYPE_PARSERS:
        return dict(type=PRIMITIVE_TYPE_PARSERS[type], default=default)

    # check if it's a typing value and it has a __origin__
    elif hasattr(type, '__origin__'):
        # check if it's typing.List
        if type.__origin__ is list:
            inner_type = type.__args__[0]
            assert inner_type in PRIMITIVE_TYPE_PARSERS, f"unsupported type {type} for argument {name}"
            assert default is None or isinstance(default, list), f"invalid default value {default} for argument {name}"
            default = default or list()
            return dict(type=PRIMITIVE_TYPE_PARSERS[inner_type], action='append', default=default)

        # check if it's typing.Dict
        elif type.__origin__ is dict:
            key_type, value_type = type.__args__
            assert key_type in PRIMITIVE_TYPE_PARSERS, f"unsupported type {type} for argument {name}"
            assert value_type in PRIMITIVE_TYPE_PARSERS, f"unsupported type {type} for argument {name}"
            assert default is None or isinstance(default, dict), f"invalid default value {default} for argument {name}"
            default = default or dict()
            return dict(
                action=ParseKVAction,
                default=default,
                key_type=key_type,
                value_type=value_type
            )

        else:
            raise Exception(f"unsupported type {type} for argument {name}")

    else:
        return dict(type=type, default=default)


def generate_subparser_for_function(subparsers: argparse._SubParsersAction, handlers: Dict[str, Callable], full_function: callable):
    annotated_args = extract_fully_annotated_args(full_function)
    unwrapped_function = full_function
    while type(unwrapped_function) is functools.partial:
        unwrapped_function = unwrapped_function.func

    param_docs, return_doc, function_doc = parse_doc(unwrapped_function.__doc__)

    # create the subparser
    try:
        short_help, _ = function_doc.split('\n\n', maxsplit=1)
    except ValueError:
        short_help = function_doc
    p: argparse.ArgumentParser = subparsers.add_parser(unwrapped_function.__name__, description=function_doc, help=short_help)

    for arg_dict in annotated_args:
        if 'value' in arg_dict:
            # already set by a functools.partial, can't be changed
            continue

        arg_name = arg_dict['name']
        arg_type = arg_dict.get('arg_type', str)
        arg_default = arg_dict.get('default', None)
        arg_doc = param_docs.get(arg_name, None)
        arg_name = arg_name.replace('_', '-')
        arg_name = '--' + arg_name if 'default' in arg_dict else arg_name
        if arg_dict['kind'] == 'positional_only':
            p.add_argument(arg_name, **parser_arg_type_keys(arg_name, arg_type, arg_default), help=arg_doc)
        elif arg_dict['kind'] == 'positional_or_keyword':
            p.add_argument(arg_name, **parser_arg_type_keys(arg_name, arg_type, arg_default), help=arg_doc)
        elif arg_dict['kind'] == 'keyword_only':
            p.add_argument(arg_name, **parser_arg_type_keys(arg_name, arg_type, arg_default), help=arg_doc)
        elif arg_dict['kind'] == 'star_args':
            p.add_argument(arg_name, **parser_arg_type_keys(arg_name, arg_type, arg_default), help=arg_doc, nargs='*')
        elif arg_dict['kind'] == 'star_kwargs':
            pass
            # p.add_argument('--' + arg_name, **parser_arg_type_keys(arg_name, arg_type, arg_default), help=arg_doc, nargs='*')
        else:
            raise Exception(f"unknown arg kind {arg_dict['kind']}")

    full_function.__cli_parser__ = p

    # add the function to the handlers
    handlers[unwrapped_function.__name__] = full_function
    return full_function


def parser_callable(subparsers, handlers):
    return functools.partial(generate_subparser_for_function, subparsers, handlers)


def subcommand_callable(super_callable, __subcommand_name, __subcommand_doc=''):
    handlers = {}

    def __handler(__subcommand_name, __subcommand_handlers, **kwargs):
        subcommand = kwargs.pop('subcommand_' + __subcommand_name)
        if subcommand is None:
            # print the usage for this subcommand
            __handler.__cli_parser__.print_help()
            return
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
from .label import *
from .wallet import *
from .credential import *