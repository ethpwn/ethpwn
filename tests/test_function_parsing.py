import functools
from ethpwn.ethlib.python_introspection_utils import extract_fully_annotated_args


def test_function_parsing_1():
    def test_func_1(a, b, /, c=None, d=None, *, e, f):
        x = 1
        y = 2
        pass

    import ipdb; ipdb.set_trace()
    annotated_args = extract_fully_annotated_args(test_func_1)
    assert annotated_args == [
        {'kind': 'positional_only', 'name': 'a'},
        {'kind': 'positional_only', 'name': 'b'},
        {'kind': 'positional_or_keyword', 'name': 'c', 'default': None},
        {'kind': 'positional_or_keyword', 'name': 'd', 'default': None},
        {'kind': 'keyword_only', 'name': 'e'},
        {'kind': 'keyword_only', 'name': 'f'},
    ]

    partial = functools.partial(test_func_1, 1, 2, 3, f=6)
    annotated_args = extract_fully_annotated_args(partial)
    assert annotated_args == [
        {'kind': 'positional_only', 'name': 'a', 'value': 1},
        {'kind': 'positional_only', 'name': 'b', 'value': 2},
        {'kind': 'positional_or_keyword', 'name': 'c', 'default': None, 'value': 3},
        {'kind': 'positional_or_keyword', 'name': 'd', 'default': None},
        {'kind': 'keyword_only', 'name': 'e'},
        {'kind': 'keyword_only', 'name': 'f', 'value': 6},
    ]

    partial = functools.partial(functools.partial(test_func_1, 1, e=3), 2, 3, f=3)
    annotated_args = extract_fully_annotated_args(partial)
    assert annotated_args == [
        {'kind': 'positional_only', 'name': 'a', 'value': 1},
        {'kind': 'positional_only', 'name': 'b', 'value': 2},
        {'kind': 'positional_or_keyword', 'name': 'c', 'default': None, 'value': 3},
        {'kind': 'positional_or_keyword', 'name': 'd', 'default': None},
        {'kind': 'keyword_only', 'name': 'e', 'value': 3},
        {'kind': 'keyword_only', 'name': 'f', 'value': 3},
    ]


def test_function_parsing_2():
    def test_func_2(a, b, /, c=None, d=None, *, e, f, **kwargs):
        z = 3

        return a, b, c, d, e, f, kwargs, z

    annotated_args = extract_fully_annotated_args(test_func_2)
    assert annotated_args == [
        {'kind': 'positional_only', 'name': 'a'},
        {'kind': 'positional_only', 'name': 'b'},
        {'kind': 'positional_or_keyword', 'name': 'c', 'default': None},
        {'kind': 'positional_or_keyword', 'name': 'd', 'default': None},
        {'kind': 'keyword_only', 'name': 'e'},
        {'kind': 'keyword_only', 'name': 'f'},
        {'kind': 'star_kwargs', 'name': 'kwargs', 'value': {}},
    ]

    assert test_func_2(1, 2, c=3, d=4, e=5, f=6, g=7, h=8) == (1, 2, 3, 4, 5, 6, {'g': 7, 'h': 8}, 3)
    assert test_func_2(1, 2, 3, d=4, e=5, f=6, g=7, h=8) == (1, 2, 3, 4, 5, 6, {'g': 7, 'h': 8}, 3)
    assert test_func_2(1, 2, 3, 4, e=5, f=6, g=7, h=8) == (1, 2, 3, 4, 5, 6, {'g': 7, 'h': 8}, 3)


    partial = functools.partial(test_func_2, 1, c=3, e=5, g=7)
    annotated_args = extract_fully_annotated_args(partial)
    assert annotated_args == [
        {'kind': 'positional_only', 'name': 'a', 'value': 1},
        {'kind': 'positional_only', 'name': 'b'},
        {'kind': 'positional_or_keyword', 'name': 'c', 'default': None, 'value': 3},
        {'kind': 'positional_or_keyword', 'name': 'd', 'default': None},
        {'kind': 'keyword_only', 'name': 'e', 'value': 5},
        {'kind': 'keyword_only', 'name': 'f'},
        {'kind': 'star_kwargs', 'name': 'kwargs', 'value': {'g': 7}},
    ]

def test_function_parsing_3():
    def test_func_3(a, b, /, c=None, d=None, *args, e, f, **kwargs):
        a = 0
        aa = 1

        return a, b, c, d, e, f, args, kwargs, aa

    annotated_args = extract_fully_annotated_args(test_func_3)
    assert annotated_args == [
        {'kind': 'positional_only', 'name': 'a'},
        {'kind': 'positional_only', 'name': 'b'},
        {'kind': 'positional_or_keyword', 'name': 'c', 'default': None},
        {'kind': 'positional_or_keyword', 'name': 'd', 'default': None},
        {'kind': 'star_args', 'name': 'args', 'value': ()},
        {'kind': 'keyword_only', 'name': 'e'},
        {'kind': 'keyword_only', 'name': 'f'},
        {'kind': 'star_kwargs', 'name': 'kwargs', 'value': {}},
    ]
    assert test_func_3(1, 2, c=3, d=4, e=5, f=6, g=7, h=8) == (0, 2, 3, 4, 5, 6, (), {'g': 7, 'h': 8}, 1)
    assert test_func_3(1, 2, 3, d=4, e=5, f=6, g=7, h=8) == (0, 2, 3, 4, 5, 6, (), {'g': 7, 'h': 8}, 1)
    assert test_func_3(1, 2, 3, 4, e=5, f=6, g=7, h=8) == (0, 2, 3, 4, 5, 6, (), {'g': 7, 'h': 8}, 1)
    assert test_func_3(1, 2, 3, 4, 10, 11, 12, e=5, f=6, g=7, h=8) == (0, 2, 3, 4, 5, 6, (10, 11, 12), {'g': 7, 'h': 8}, 1)

    partial = functools.partial(test_func_3, 1, c=3, e=5, g=7)
    annotated_args = extract_fully_annotated_args(partial)
    assert annotated_args == [
        {'kind': 'positional_only', 'name': 'a', 'value': 1},
        {'kind': 'positional_only', 'name': 'b'},
        {'kind': 'positional_or_keyword', 'name': 'c', 'default': None, 'value': 3},
        {'kind': 'positional_or_keyword', 'name': 'd', 'default': None},
        {'kind': 'star_args', 'name': 'args', 'value': ()},
        {'kind': 'keyword_only', 'name': 'e', 'value': 5},
        {'kind': 'keyword_only', 'name': 'f'},
        {'kind': 'star_kwargs', 'name': 'kwargs', 'value': {'g': 7}},
    ]
    assert partial(2, d=4, f=6, h=8) == (0, 2, 3, 4, 5, 6, (), {'g': 7, 'h': 8}, 1)

    partial = functools.partial(functools.partial(test_func_3, 1, e=5), 2, 3, f=6, d=4)
    annotated_args = extract_fully_annotated_args(partial)
    assert annotated_args == [
        {'kind': 'positional_only', 'name': 'a', 'value': 1},
        {'kind': 'positional_only', 'name': 'b', 'value': 2},
        {'kind': 'positional_or_keyword', 'name': 'c', 'default': None, 'value': 3},
        {'kind': 'positional_or_keyword', 'name': 'd', 'default': None, 'value': 4},
        {'kind': 'star_args', 'name': 'args', 'value': ()},
        {'kind': 'keyword_only', 'name': 'e', 'value': 5},
        {'kind': 'keyword_only', 'name': 'f', 'value': 6},
        {'kind': 'star_kwargs', 'name': 'kwargs', 'value': {}},
    ]
    assert partial(h=9) == (0, 2, 3, 4, 5, 6, (), {'h': 9}, 1)

    partial = functools.partial(functools.partial(test_func_3, 1, e=5), 2, 3, 4, 10, 11, 12, f=6)
    annotated_args = extract_fully_annotated_args(partial)
    assert annotated_args == [
        {'kind': 'positional_only', 'name': 'a', 'value': 1},
        {'kind': 'positional_only', 'name': 'b', 'value': 2},
        {'kind': 'positional_or_keyword', 'name': 'c', 'default': None, 'value': 3},
        {'kind': 'positional_or_keyword', 'name': 'd', 'default': None, 'value': 4},
        {'kind': 'star_args', 'name': 'args', 'value': (10, 11, 12)},
        {'kind': 'keyword_only', 'name': 'e', 'value': 5},
        {'kind': 'keyword_only', 'name': 'f', 'value': 6},
        {'kind': 'star_kwargs', 'name': 'kwargs', 'value': {}},
    ]
    assert partial(7, 8, h=9) == (0, 2, 3, 4, 5, 6, (10, 11, 12, 7, 8), {'h': 9}, 1)


def test_function_parsing_all_defaults():
    def test_func_all_defaults(a=1, b=2, /, c=3, d=4, *args, e=5, f=6, **kwargs):
        a = 0
        aa = 1

        return a, b, c, d, e, f, args, kwargs, aa

    import ipdb; ipdb.set_trace()

    annotated_args = extract_fully_annotated_args(test_func_all_defaults)
    assert annotated_args == [
        {'kind': 'positional_only', 'name': 'a', 'default': 1},
        {'kind': 'positional_only', 'name': 'b', 'default': 2},
        {'kind': 'positional_or_keyword', 'name': 'c', 'default': 3},
        {'kind': 'positional_or_keyword', 'name': 'd', 'default': 4},
        {'kind': 'star_args', 'name': 'args', 'value': ()},
        {'kind': 'keyword_only', 'name': 'e', 'default': 5},
        {'kind': 'keyword_only', 'name': 'f', 'default': 6},
        {'kind': 'star_kwargs', 'name': 'kwargs', 'value': {}},
    ]
    assert test_func_all_defaults(1, 2, c=3, d=4, e=5, f=6, g=7, h=8) == (0, 2, 3, 4, 5, 6, (), {'g': 7, 'h': 8}, 1)
    assert test_func_all_defaults(1, 2, 3, d=4, e=5, f=6, g=7, h=8) == (0, 2, 3, 4, 5, 6, (), {'g': 7, 'h': 8}, 1)
    assert test_func_all_defaults(1, 2, 3, 4, e=5, f=6, g=7, h=8) == (0, 2, 3, 4, 5, 6, (), {'g': 7, 'h': 8}, 1)
    assert test_func_all_defaults(1, 2, 3, 4, 10, 11, 12, e=5, f=6, g=7, h=8) == (0, 2, 3, 4, 5, 6, (10, 11, 12), {'g': 7, 'h': 8}, 1)

    partial = functools.partial(test_func_all_defaults, 1, c=3, e=5, g=7)
    annotated_args = extract_fully_annotated_args(partial)
    assert annotated_args == [
        {'kind': 'positional_only', 'name': 'a', 'default': 1, 'value': 1},
        {'kind': 'positional_only', 'name': 'b', 'default': 2},
        {'kind': 'positional_or_keyword', 'name': 'c', 'default': 3, 'value': 3},
        {'kind': 'positional_or_keyword', 'name': 'd', 'default': 4},
        {'kind': 'star_args', 'name': 'args', 'value': ()},
        {'kind': 'keyword_only', 'name': 'e', 'default': 5, 'value': 5},
        {'kind': 'keyword_only', 'name': 'f', 'default': 6},
        {'kind': 'star_kwargs', 'name': 'kwargs', 'value': {'g': 7}},
    ]
    assert partial(2, d=4, f=6, h=8) == (0, 2, 3, 4, 5, 6, (), {'g': 7, 'h': 8}, 1)

    partial = functools.partial(functools.partial(test_func_all_defaults, 1, e=5), 2, 3, f=6, d=4)
    annotated_args = extract_fully_annotated_args(partial)
    assert annotated_args == [
        {'kind': 'positional_only', 'name': 'a', 'default': 1, 'value': 1},
        {'kind': 'positional_only', 'name': 'b', 'default': 2, 'value': 2},
        {'kind': 'positional_or_keyword', 'name': 'c', 'default': 3, 'value': 3},
        {'kind': 'positional_or_keyword', 'name': 'd', 'default': 4, 'value': 4},
        {'kind': 'star_args', 'name': 'args', 'value': ()},
        {'kind': 'keyword_only', 'name': 'e', 'default': 5, 'value': 5},
        {'kind': 'keyword_only', 'name': 'f', 'default': 6, 'value': 6},
        {'kind': 'star_kwargs', 'name': 'kwargs', 'value': {}},
    ]
    assert partial(h=9) == (0, 2, 3, 4, 5, 6, (), {'h': 9}, 1)

    partial = functools.partial(functools.partial(test_func_all_defaults, 1, e=5), 2, 3, 4, 10, 11, 12, f=6)
    annotated_args = extract_fully_annotated_args(partial)
    assert annotated_args == [
        {'kind': 'positional_only', 'name': 'a', 'default': 1, 'value': 1},
        {'kind': 'positional_only', 'name': 'b', 'default': 2, 'value': 2},
        {'kind': 'positional_or_keyword', 'name': 'c', 'default': 3, 'value': 3},
        {'kind': 'positional_or_keyword', 'name': 'd', 'default': 4, 'value': 4},
        {'kind': 'star_args', 'name': 'args', 'value': (10, 11, 12)},
        {'kind': 'keyword_only', 'name': 'e', 'default': 5, 'value': 5},
        {'kind': 'keyword_only', 'name': 'f', 'default': 6, 'value': 6},
        {'kind': 'star_kwargs', 'name': 'kwargs', 'value': {}},
    ]
    assert partial(7, 8, h=9) == (0, 2, 3, 4, 5, 6, (10, 11, 12, 7, 8), {'h': 9}, 1)

if __name__ == '__main__':
    for f in list(globals().values()):
        if callable(f) and getattr(f, '__name__', '').startswith('test_'):
            f()
            print(f"{f.__name__} passed")
    print("All passed")