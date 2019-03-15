from . import cst
from . import errors
from . import lexer
from mtots import test
from mtots.parser import base
from mtots.parser import combinator
from mtots.parser.combinator import All
from mtots.parser.combinator import Any
from mtots.parser.combinator import AnyTokenBut
from mtots.parser.combinator import Forward
from mtots.parser.combinator import Peek
from mtots.parser.combinator import Required
from mtots.parser.combinator import Token


def Struct(*args, **kwargs):
    return combinator.Struct(*args, include_mark=True, **kwargs)


module = Forward(lambda: Struct(cst.Module, [
    ['statements', Any(
        All(import_),
        All(global_variable),
        All(function),
        All(class_),
        All('NEWLINE').valmap(()),
    ).repeat().flatten().map(tuple)],
]))

import_ = Struct(cst.Import, [
    'import',
    ['name', All(
        All('ID'),
        All('.', 'ID').getitem(1).repeat(),
    ).flatten().map('.'.join)],
    ['alias', Any(
        All('as', 'ID').getitem(1),
        All().valmap(None),
    )],
])

global_variable = Forward(lambda: Struct(cst.GlobalVariable, [
    'var',
    ['name', Required('ID')],
    Required(':'),
    ['type', type_expression.required()],
    Required('NEWLINE'),
]))

class_ = Forward(lambda: Struct(cst.Class, [
    ['native', Any('native').optional()],
    'class',
    ['name', Required('ID')],
    ['type_parameters', Any(
        type_parameters,
        All().valmap(None),
    )],
    ['base', Any(
        All('(', type_expression.required(), Required(')')).getitem(1),
        All().valmap(None),
    )],
    ['members', All(
        '{',
        Any(
            All(field),
            All('NEWLINE').valmap(()),
        ).repeat().flatten().map(tuple),
        '}',
    ).getitem(1).required()],
]))

field = Forward(lambda: Struct(cst.Field, [
    'var',
    ['name', 'ID'],
    ':',
    ['type', type_expression],
]))

parameter = Forward(lambda: Struct(cst.Parameter, [
    ['name', 'ID'],
    ':',
    ['type', type_expression],
]))
parameters = All('(', parameter.join(','), ')').getitem(1).map(tuple)

function = Forward(lambda: Struct(cst.Function, [
    ['native', Any('native').optional()],
    'def',
    ['name', Required('ID')],
    ['type_parameters', Any(
        type_parameters,
        All().valmap(None),
    )],
    ['parameters', parameters.required()],
    Required(':'),
    ['return_type', type_expression.required()],
    ['body', Any(
        All('NEWLINE').valmap(None),
        All(
            Required('='),
            value_expression.required(),
            'NEWLINE',
        ).getitem(1),
    )],
]))

type_expression = Forward(lambda: Any(
    Struct(cst.VoidType, ['void']),
    Struct(cst.IntType, ['int']),
    Struct(cst.DoubleType, ['double']),
    Struct(cst.StringType, ['string']),
    Struct(cst.Typename, [['name', 'ID']]),
    Struct(cst.GenericType, [
        ['name', 'ID'],
        ['types', All(
            '[',
            type_expression.join(','),
            Required(']'),
        ).getitem(1)],
    ]),
))

type_parameter = Struct(cst.TypeParameter, [
    ['name', 'ID'],
    ['base', Any(
        All(':', type_expression).getitem(1),
        All().valmap(None),
    )],
])
type_parameters = All(
    '[', type_parameter.join(','), ']',
).getitem(1).map(tuple)

value_expression = Forward(lambda: Any(
    atom,
))
block = Struct(cst.Block, [
    '{',
    Any('NEWLINE').optional(),
    ['expressions', value_expression.join('NEWLINE').map(tuple)],
    Any('NEWLINE').optional(),
    Required('}'),
])
atom = Any(
    block,
)


def _parse_pattern(pattern, data, path):
    return combinator.parse_pattern(
        pattern=pattern,
        data=data,
        path=path,
        lexer=lexer,
    )


def parse(data, *, path='<string>'):
    return _parse_pattern(module, data, path)


@test.case
def test_sample():
    # For now, just check parse doesn't throw
    parse(r"""
    import abc.foo
    class Foo {
        var x: int
    }
    class Bar[T](Foo) {
        var t: T
    }
    def foo(a: int, b: int): void = {}
    """)

