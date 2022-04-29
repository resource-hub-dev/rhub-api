import pytest

from rhub.api import utils


@pytest.mark.parametrize(
    'condition, params, result',
    [
        (
            ['param_eq', 'foo', 'bar'],
            {'foo': 'bar'},
            True,
        ),
        (
            ['param_eq', 'foo', 'bar'],
            {'foo': ''},
            False,
        ),
        (
            ['param_eq', 'foo', '0'],
            {'foo': 0},
            False,
        ),
        (
            ['param_ne', 'foo', 'bar'],
            {'foo': 'bar'},
            False,
        ),
        (
            ['param_ne', 'foo', 'bar'],
            {'foo': ''},
            True,
        ),
        (
            ['param_ne', 'foo', '0'],
            {'foo': 0},
            True,
        ),
        (
            ['not', ['param_eq', 'foo', 'bar']],
            {'foo': 'bar'},
            False,
        ),
        (
            ['not', ['param_eq', 'foo', 'bar']],
            {'foo': ''},
            True,
        ),
        (
            ['and', ['param_eq', 'foo', 'bar'], ['param_eq', 'x', 'abc']],
            {'foo': 'bar', 'x': 'abc'},
            True,
        ),
        (
            ['and', ['param_eq', 'foo', 'bar'], ['param_eq', 'x', 'abc']],
            {'foo': 'bar', 'bar': ''},
            False,
        ),
        (
            ['not', ['and', ['param_eq', 'foo', 'bar'], ['param_eq', 'x', 'abc']]],
            {'foo': 'bar', 'x': 'abc'},
            False,
        ),
        (
            ['or', ['param_eq', 'foo', 'bar'], ['param_eq', 'x', 'abc']],
            {'foo': 'bar', 'x': 'abc'},
            True,
        ),
        (
            ['or', ['param_eq', 'foo', 'bar'], ['param_eq', 'x', 'abc']],
            {'foo': 'bar', 'bar': ''},
            True,
        ),
        (
            ['or', ['param_eq', 'foo', 'bar'], ['param_eq', 'x', 'abc']],
            {'foo': '', 'bar': ''},
            False,
        ),
        (
            ['not', ['or', ['param_eq', 'foo', 'bar'], ['param_eq', 'x', 'abc']]],
            {'foo': '', 'bar': ''},
            True,
        ),
        (
            [
                'or',
                ['and', ['param_eq', 'foo', ''], ['param_eq', 'x', '']],
                ['and', ['param_eq', 'foo', 'bar'], ['param_eq', 'x', 'abc']],
            ],
            {'foo': 'bar', 'x': 'abc'},
            True,
        ),
    ]
)
def test_condition_eval(condition, params, result):
    assert utils.condition_eval(condition, params) == result
