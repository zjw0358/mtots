from . import cst
from . import errors
from . import lexer
from . import types
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
from mtots.util import Scope
import os
from mtots.util import typing


def Struct(*args, **kwargs):
    return combinator.Struct(*args, include_mark=True, **kwargs)


translation_unit = Forward(lambda: Struct(cst.TranslationUnit, [
    ['stmts', Any(
        inline_blob,
        import_stmt,
        native_typedef,
        struct_definition,
        function_definition,
    ).repeat()],
]))

inline_blob = Struct(cst.InlineBlob, [
    'inline',
    ['type', Any(
        All('*', '*').valmap('fwd'),
        All('*').valmap('hdr'),
        All().valmap('src'),
    )],
    ['text', Required('STR')],
])

import_path_pattern = All(
    All('ID'),
    All('.', 'ID').getitem(1).repeat(),
).flatten().map('.'.join)

import_stmt = Struct(cst.Import, [
    'import',
    ['path', import_path_pattern],
])

native_typedef = Struct(cst.NativeTypedef, [
    'native', 'typedef', ['name', Required('ID')],
])

native = Any('native').optional().map(bool)
typedef = Any('typedef').optional().map(bool)

primitive_type_ref = Struct(cst.PrimitiveType, [['type', Any(
    All('void').valmap(types.VOID),
    All('char').valmap(types.CHAR),
    All('signed', 'char').valmap(types.SIGNED_CHAR),
    All('unsigned', 'char').valmap(types.UNSIGNED_CHAR),
    All('short').valmap(types.SHORT),
    All('unsigned', 'short').valmap(types.UNSIGNED_SHORT),
    All('int').valmap(types.INT),
    All('unsigned', 'int').valmap(types.UNSIGNED_INT),
    All('long', 'long').valmap(types.LONG_LONG),
    All('unsigned', 'long', 'long').valmap(types.UNSIGNED_LONG_LONG),
    All('long').valmap(types.LONG),
    All('unsigned', 'long').valmap(types.UNSIGNED_LONG),
    All('float').valmap(types.FLOAT),
    All('double').valmap(types.DOUBLE),
    All('long', 'double').valmap(types.LONG_DOUBLE),
)]])

simple_type_ref = Any(
    Struct(cst.NamedType, [['name', 'ID']]),
    primitive_type_ref,
)

type_ref = Forward(lambda: Any(
    Struct(cst.PointerType, [['type', type_ref], '*']),
    Struct(cst.ConstType, [['type', type_ref], 'const']),
    Struct(cst.FunctionType, [
        ['rtype', type_ref],
        '(',
        ['ptypes', type_ref.join(',')],
        ['varargs', Any(
            All(',', '...').valmap(True),
            All(',').optional().valmap(False),
        )],
        ')',
    ]),
    Struct(cst.ConstType, ['const', ['type', simple_type_ref]]),
    simple_type_ref
        .recover(lambda m: base.Failure(m.mark, 'Expected type')),
))

expression = Forward(lambda: additive)

statement = Forward(lambda: Any(
    block,
    declaration_statement,
    return_statement,
    expression_statement,
))

global_variable_declaration = Struct(cst.GlobalVariableDeclaration, [
    ['native', native],
    ['type', type_ref],
    ['name', 'ID'],
])

field_definition = Struct(cst.Field, [
    ['type', type_ref],
    ['name', 'ID'],
])

struct_definition = Struct(cst.StructDefinition, [
    ['native', native],
    ['typedef', typedef],
    'struct',
    ['name', 'ID'],
    ['fields', Any(
        All(
            '{',
            field_definition.repeat(),
            Required('}'),
        ).getitem(1),
        Any(';').valmap(None),
    )],
])

parameter = Struct(cst.Parameter, [
    ['type', type_ref],
    ['name', 'ID'],
])

function_definition = Forward(lambda: Struct(cst.FunctionDefinition, [
    ['rtype', type_ref],
    ['name', 'ID'],
    '(',
    ['params', parameter.join(',')],
    ['varargs', Any(
        All(',', '...').valmap(True),
        All(',').optional().valmap(False),
    )],
    Required(')'),
    ['body', Any(
        block,
        Any(';').valmap(None),
    ).required()],
]))


########################################################################
# Statements
########################################################################

block = Struct(cst.Block, [
    '{',
    ['stmts', statement.repeat()],
    Required('}'),
])

declaration_statement = Struct(cst.LocalVariableDeclaration, [
    ['type', type_ref],
    ['name', 'ID'],
    ['expr', Any(
        All('=', expression).getitem(1),
        All().valmap(None),
    )],
    Required(';'),
])

return_statement = Struct(cst.Return, [
    'return', ['expr', Any(expression, All().valmap(None))], Required(';'),
])

expression_statement = Struct(cst.ExpressionStatement, [
    ['expr', expression], Required(';'),
])


########################################################################
# Expressions
########################################################################

atom = Any(
    All('(', expression.required(), Required(')')).getitem(1),
    Struct(cst.IntLiteral, [['value', 'INT']]),
    Struct(cst.DoubleLiteral, [['value', 'DOUBLE']]),
    Struct(cst.StringLiteral, [['value', 'STR']]),
    Struct(cst.Variable, [['name', 'ID']]),
)

postfix = Forward(lambda: Any(
    Struct(cst.FunctionCall, [
        ['f', postfix],
        '(',
        ['args', expression.join(',')],
        Required(')'),
    ]),
    atom,
))

unop = Any(
    Struct(cst.Unop, [
        ['op', Any('+', '-', '*', '&')],
        ['expr', postfix],
    ]),
    postfix,
)

multiplicative = Any(
    Struct(cst.Binop, [
        ['left', unop],
        ['op', Any('*', '/', '%')],
        ['right', unop],
    ]),
    unop,
)

additive = Any(
    Struct(cst.Binop, [
        ['left', multiplicative],
        ['op', Any('*', '/', '%')],
        ['right', multiplicative],
    ]),
    multiplicative,
)


########################################################################
# actual parsing functions
########################################################################


def _parse_pattern(pattern, data, file_path):
    source = base.Source(data=data, path=file_path)
    tokens = lexer.lex(source)
    match_result = All(pattern, Peek('EOF')).getitem(0).parse(tokens)
    if not match_result:
        raise match_result.to_error()
    return match_result.value


def parse(data, *, file_path='<string>'):
    return _parse_pattern(
        pattern=translation_unit,
        data=data,
        file_path=file_path,
    )


@test.case
def test_simple_case():
    # TODO: Actually check the result
    # For now, just check that the parse is successful
    parse("""
    import stdio

    int main(int argc, char **argv) {
        return 0;
    }
    """)
