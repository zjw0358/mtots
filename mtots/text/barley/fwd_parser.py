from . import fwd_ast as ast
from . import lexer
from mtots import test
from mtots.text.combinator import All
from mtots.text.combinator import Any
from mtots.text.combinator import AnyTokenBut
from mtots.text.combinator import AnyTokenNotAt
from mtots.text.combinator import Forward
from mtots.text.combinator import Peek
from mtots.text.combinator import Success

delimiter = Any('NEWLINE', ';')

primitive_type_names = ('void', 'int', 'double')

non_delimiter = AnyTokenNotAt(delimiter)

import_declaration = All(
    'import',
    non_delimiter.repeat(),
    delimiter,
).map(lambda v: [])

empty_declaration = delimiter.map(lambda v: [])

block = Forward(lambda: All(
    Any('NEWLINE').optional(),
    'INDENT',
    Any(
        AnyTokenBut('INDENT', 'DEDENT'),
        block,
    ),
    'DEDENT',
))

class_declaration = All(
    Any('native').optional(),
    Any('class', 'trait'),
    'ID',
    non_delimiter.repeat(),
    block,
).fatmap(lambda r: [ast.Entry(r.mark, r.value[1], r.values[0])])

global_variable_declaration = All(
    'ID', '=', non_delimiter.repeat(), delimiter,
).fatmap(lambda r: [ast.Entry(r.mark, r.value[0], 'var')])

type_ref = Forward(lambda: Any(
    All(
        type_ref,
        '[',
        All(type_ref, Any(',').optional()).repeat(),
        ']',
    ),
    All('ID', '.', type_ref),
    'ID',
    *primitive_type_names,
))

function_declaration = All(
    Any('native').optional(),
    type_ref,
    'ID',
    non_delimiter.repeat(),
    block,
)

module = All(
    Any(
        import_declaration,
        empty_declaration,
    ).repeat(),
    Any(
        class_declaration,
        function_declaration,
        global_variable_declaration,
        empty_declaration,
    ).repeat(),
    Peek('EOF'),
).flatten().fatmap(lambda r: ast.Module(r.mark, r.value))


def _parse_string(s):
    tokens = lexer.lex_string(s)
    return function_declaration.parse(tokens)


@test.case
def test_sample():
    r = _parse_string("""int foo
    pass
""")
    print(r)
