
import functools
import inspect

# dammit i reimplemented `inspect.signature` -.-
# but at least this supports removing the args from `partials`
def extract_args_from_function(unwrapped_func: callable):
    while type(unwrapped_func) is functools.partial:
        unwrapped_func = unwrapped_func.func

    defaults = unwrapped_func.__defaults__ or []
    kwd_defaults = unwrapped_func.__kwdefaults__ or {}

    pos_arg_names = unwrapped_func.__code__.co_varnames[:unwrapped_func.__code__.co_argcount]
    kwarg_names = unwrapped_func.__code__.co_varnames[unwrapped_func.__code__.co_argcount:][:unwrapped_func.__code__.co_kwonlyargcount]
    index_done = unwrapped_func.__code__.co_argcount + unwrapped_func.__code__.co_kwonlyargcount
    if unwrapped_func.__code__.co_flags & inspect.CO_VARARGS:
        star_arg_name = unwrapped_func.__code__.co_varnames[index_done]
        index_done += 1
    else:
        star_arg_name = None
    if unwrapped_func.__code__.co_flags & inspect.CO_VARKEYWORDS:
        star_kwarg_name = unwrapped_func.__code__.co_varnames[index_done]
        index_done += 1
    else:
        star_kwarg_name = None

    pos_only_args = pos_arg_names[:unwrapped_func.__code__.co_posonlyargcount]
    pos_or_kwarg_args = pos_arg_names[unwrapped_func.__code__.co_posonlyargcount:]

    pos_args = pos_only_args + pos_or_kwarg_args
    kwargs = list(kwarg_names)

    defaults = unwrapped_func.__defaults__ or []
    kwd_defaults = unwrapped_func.__kwdefaults__ or {}

    defaults_for_pos_args = dict(reversed(list(zip(reversed(pos_args), reversed(defaults)))))
    assert set(defaults_for_pos_args.keys()) & set(kwd_defaults.keys()) == set(), "positional args and kwargs cannot have the same name"

    all_defaults = {**defaults_for_pos_args, **kwd_defaults}
    all_types = {**unwrapped_func.__annotations__}

    annotated = []
    for arg in pos_only_args:
        annotated.append(dict(
            kind='positional_only',
            name=arg,
            **({} if arg not in all_defaults else {'default': all_defaults[arg]}),
            **({} if arg not in all_types else {'arg_type': all_types[arg]}),
        ))
    for arg in pos_or_kwarg_args:
        annotated.append(dict(
            kind='positional_or_keyword',
            name=arg,
            **({} if arg not in all_defaults else {'default': all_defaults[arg]}),
            **({} if arg not in all_types else {'arg_type': all_types[arg]}),
        ))

    if star_arg_name is not None:
        assert star_arg_name not in all_defaults, "star args cannot have a default"

        annotated.append(dict(
            kind='star_args',
            name=star_arg_name,
            **({} if star_arg_name not in all_types else {'arg_type': all_types[star_arg_name]})
        ))

    for arg in kwarg_names:
        annotated.append(dict(
            kind='keyword_only',
            name=arg,
            **({} if arg not in all_defaults else {'default': all_defaults[arg]}),
            **({} if arg not in all_types else {'arg_type': all_types[arg]}),
        ))

    if star_kwarg_name is not None:
        assert star_kwarg_name not in all_defaults, "star kwargs cannot have a default"
        annotated.append(dict(
            kind='star_kwargs',
            name=star_kwarg_name,
            **({} if star_kwarg_name not in all_types else {'arg_type': all_types[star_kwarg_name]})
        ))

    return annotated


def _get_partial_func_args(partial_func: functools.partial):
    # recurse if it's a partial of a partial
    args, keywords = [], {}
    if type(partial_func) is functools.partial:
        args, keywords = _get_partial_func_args(partial_func.func)
        args = list(partial_func.args) + list(args)
        keywords.update(partial_func.keywords)
    return tuple(args), keywords

def annotate_args_with_partial_values(maybe_partial_func, annotated_args):
    partial_args, partial_kwargs = _get_partial_func_args(maybe_partial_func)

    star_args_pos_start = 0
    consumed_kwargs = set()
    can_have_star_args = True
    for arg_idx, arg_dict in enumerate(annotated_args):
        if arg_dict['kind'] == 'positional_only':
            if arg_idx < len(partial_args):
                assert arg_dict['name'] not in partial_kwargs, "purely positional args cannot be passed as kwargs"
                arg_dict['value'] = partial_args[arg_idx]
                star_args_pos_start = arg_idx + 1
        elif arg_dict['kind'] == 'positional_or_keyword':
            if arg_idx < len(partial_args):
                assert arg_dict['name'] not in partial_kwargs, f"conflicting values for positional_or_keyword arg {arg_dict['name']}"
                arg_dict['value'] = partial_args[arg_idx]
                star_args_pos_start = arg_idx + 1
            elif arg_dict['name'] in partial_kwargs:
                arg_dict['value'] = partial_kwargs[arg_dict['name']]
                # if positional args are passed via kwargs, then we can no longer pass positional args
                can_have_star_args = False
                consumed_kwargs.add(arg_dict['name'])
        elif arg_dict['kind'] == 'keyword_only':
            if arg_dict['name'] in partial_kwargs:
                arg_dict['value'] = partial_kwargs[arg_dict['name']]
                consumed_kwargs.add(arg_dict['name'])
        elif arg_dict['kind'] == 'star_args':
            assert arg_dict['name'] not in partial_kwargs, "star args cannot be passed as kwargs"
            if can_have_star_args:
                arg_dict['value'] = partial_args[star_args_pos_start:]
            else:
                assert len(partial_args[star_args_pos_start:]) == 0, "star args cannot be passed after kwargs were used to set positional args"
                arg_dict['value'] = ()
        elif arg_dict['kind'] == 'star_kwargs':
            assert arg_dict['name'] not in partial_kwargs, "star kwargs cannot be passed as kwargs"
            arg_dict['value'] = {k: v for k, v in partial_kwargs.items() if k not in consumed_kwargs}
            consumed_kwargs.update(arg_dict['value'].keys())
        else:
            raise Exception(f"unknown arg kind {arg_dict['kind']}")

    assert len(partial_kwargs.keys() - consumed_kwargs) == 0, f"unknown kwargs {partial_kwargs.keys() - consumed_kwargs}"

    return annotated_args

def annotate_args_with_types(function, annotated_args):
    while type(function) is functools.partial:
        function = function.func

    types = function.__annotations__
    for arg_dict in annotated_args:
        if arg_dict['name'] in types:
            arg_dict['arg_type'] = types[arg_dict['name']]

    return annotated_args


def parse_doc(doc: str):
    param_docs = {}
    return_doc = None
    real_doc = ''
    if not doc:
        return param_docs, return_doc, real_doc

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

def annotate_args_with_docs(function, annotated_args):
    while type(function) is functools.partial:
        function = function.func

    param_docs, return_doc, function_doc = parse_doc(function.__doc__)
    for arg_dict in annotated_args:
        if arg_dict['name'] in param_docs:
            arg_dict['help'] = param_docs[arg_dict['name']]

    return annotated_args

def extract_fully_annotated_args(function):
    annotated_args = extract_args_from_function(function)
    annotated_args = annotate_args_with_partial_values(function, annotated_args)
    annotated_args = annotate_args_with_types(function, annotated_args)
    annotated_args = annotate_args_with_docs(function, annotated_args)
    return annotated_args

