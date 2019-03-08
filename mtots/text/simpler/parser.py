from . import cst
from . import errors
from . import lexer
from mtots import test
from mtots.text import base
from mtots.text import combinator
from mtots.text.combinator import All
from mtots.text.combinator import Any
from mtots.text.combinator import AnyTokenBut
from mtots.text.combinator import Forward
from mtots.text.combinator import Peek
from mtots.text.combinator import Required
from mtots.text.combinator import Token


def Struct(*args, **kwargs):
    return combinator.Struct(*args, include_mark=True, **kwargs)

type_expression = Forward(lambda: Any(
    Struct(cst.ReifiedType, [
        ['name', 'ID'],
        '[',
        ['type_arguments', type_expression.join(',').map(tuple)],
        Any(',').optional(),
        Required(']'),
    ]),
    Struct(cst.VoidType, ['void']),
    Struct(cst.BoolType, ['bool']),
    Struct(cst.IntType, ['int']),
    Struct(cst.DoubleType, ['double']),
    Struct(cst.StringType, ['string']),
    Struct(cst.Typename, [['name', 'ID']]),
))

value_expression = Forward(lambda: atom)

file_ = Forward(lambda: Struct(cst.File, [
    ['statements', Any(
        All(import_),
        All(class_),
        All(function),
        All('NEWLINE').valmap(()),
    ).repeat().flatten().map(tuple)],
]))

import_ = Struct(cst.Import, [
    'import',
    ['name', All(
        All('ID'),
        All('.', 'ID').getitem(1).repeat(),
    ).flatten().map('.'.join)],
    Required('NEWLINE')
])

field = Struct(cst.Field, [
    ['type', type_expression],
    ['name', 'ID'],
])

type_parameter = Struct(cst.TypeParameter, [
    ['name', 'ID'],
    ['base', Any(
        All('<', type_expression).getitem(1),
        All().valmap(None),
    )],
])

type_parameters = All(
    '[',
    type_parameter.join(',').map(tuple),
    Required(']'),
).getitem(1)

maybe_type_parameters = Any(
    type_parameters,
    All().valmap(None),
)

class_ = Struct(cst.Class, [
    ['native', Any('native').optional()],
    'class',
    ['name', Required('ID')],
    ['type_parameters', maybe_type_parameters],
    ['base', Any(
        All('<', type_expression).getitem(1),
        All().valmap(None),
    )],
    Required('{'),
    ['fields', All(
        All('NEWLINE').optional(),
        field.join('NEWLINE').map(tuple),
        All('NEWLINE').optional(),
    ).getitem(1)],
    Required('}'),
])

parameter = Struct(cst.Parameter, [
    ['type', type_expression],
    ['name', 'ID'],
])

parameters = All(
    '(',
    parameter.join(',').map(tuple),
    Any(',').optional(),
    Required(')'),
).getitem(1)

function = Struct(cst.Function, [
    ['native', Any('native').optional()],
    ['return_type', type_expression],
    ['name', Required('ID')],
    ['type_parameters', maybe_type_parameters],
    ['parameters', parameters.required()],
    ['body', Any(
        All('NEWLINE').valmap(None),
        All('=', value_expression).required().getitem(1),
    )],
])

atom = Any(
    All('(', value_expression, Required(')')).getitem(1),
    Struct(cst.Block, [
        '{',
        Any('NEWLINE').optional(),
        ['expressions', value_expression.join('NEWLINE').map(tuple)],
        Any('NEWLINE').optional(),
        Required('}'),
    ]),
    Struct(cst.Bool, [
        ['value', Any(
            All('true').valmap(True),
            All('false').valmap(False),
        )],
    ]),
    Struct(cst.Int, [['value', 'INT']]),
    Struct(cst.Double, [['value', 'DOUBLE']]),
    Struct(cst.String, [['value', 'STR']]),
)


def parse(data, *, path='<string>'):
    return combinator.parse_pattern(
        pattern=file_,
        data=data,
        path=path,
        lexer=lexer,
    )


@test.case
def test_sanity():
    # For now, just check this doesn't throw
    parse(r"""
    import abc
    native class List[T] {}
    class Foo < Base {
        string x
        Base base
    }
    List[T] sort[T < Comparable[T]](List[T] list)
    string foo() = 'hello world'
    int main() = 0
    """)
