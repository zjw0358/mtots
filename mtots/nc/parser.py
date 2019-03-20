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

value_expression = Forward(lambda: postfix)

file_ = Forward(lambda: Struct(cst.File, [
    ['statements', Any(
        All(import_),
        All(inline),
        All(class_),
        All(function),
        All('NEWLINE').valmap(()),
    ).repeat().flatten().map(tuple)],
]))

module_name = All(
    All('ID'),
    All('.', 'ID').getitem(1).repeat(),
).flatten().map('.'.join)

import_ = Struct(cst.Import, [
    'from',
    ['module', module_name.required()],
    Required('import'),
    ['name', Required('ID')],
    ['alias', Any(
        All('as', 'ID').getitem(1),
        All().valmap(None),
    )],
    Required('NEWLINE')
])

inline = Struct(cst.Inline, [
    'inline',
    ['name', Required('ID')],
    ['type', Required('STR')],
    ['text', Required('STR')],
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
        Peek('NEWLINE').valmap(None),
        All('=', value_expression).required().getitem(1),
    )],
])

field = Struct(cst.Field, [
    ['type', type_expression],
    ['name', 'ID'],
])

method = Struct(cst.Method, [
    ['abstract', Any('abstract').optional()],
    ['return_type', type_expression],
    ['name', Required('ID')],
    ['parameters', parameters],
    ['body', Any(
        Peek('NEWLINE').valmap(None),
        All('=', value_expression).required().getitem(1),
    )],
])

class_ = Struct(cst.Class, [
    ['native', Any('native').optional()],
    ['is_trait', Any(
        All('class').valmap(False),
        All('trait').valmap(True),
    )],
    ['name', Required('ID')],
    ['type_parameters', maybe_type_parameters],
    ['base', Any(
        All('<', type_expression).getitem(1),
        All().valmap(None),
    )],
    Required('{'),
    ['fields_and_methods', All(
        All('NEWLINE').optional(),
        Any(method, field).join('NEWLINE').map(tuple),
        All('NEWLINE').optional(),
    ).getitem(1)],
    Required('}'),
])

local_variable_declaration = Struct(cst.LocalVariableDeclaration, [
    ['type', Any(
        type_expression,
        All('final').valmap(None),
    )],
    ['name', 'ID'],
    Required('='),
    ['expression', value_expression.required()],
])

atom = Forward(lambda: Any(
    All('(', value_expression, Required(')')).getitem(1),
    Struct(cst.Block, [
        '{',
        Any('NEWLINE').optional(),
        ['expressions', Any(
            local_variable_declaration,
            value_expression,
        ).join('NEWLINE').map(tuple)],
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
    Struct(cst.Name, [['value', 'ID']]),
    Struct(cst.New, [
        'new',
        Required('('),
        ['type', type_expression.required()],
        Required(')'),
    ]),
))

arguments = All(
    '(',
    value_expression.join(',').map(tuple),
    Any(',').optional(),
    Required(')'),
).getitem(1)

postfix = Forward(lambda: Any(
    Struct(cst.FunctionCall, [
        ['name', 'ID'],
        ['type_arguments', Any(
            All(
                '[',
                type_expression.join(',').map(tuple),
                Any(',').optional(),
                ']',
            ).getitem(1),
            All().valmap(None),
        )],
        ['arguments', arguments],
    ]),
    Struct(cst.MethodCall, [
        ['owner', atom],
        '.',
        ['name', 'ID'],
        ['arguments', arguments],
    ]),
    atom,
))


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
    from abc import foo
    native class List[T] {}
    class Foo < Base {
        string x
        Base base
    }
    List[T] sort[T < Comparable[T]](List[T] list)
    string foo() = 'hello world'
    int main() = 0
    """)
