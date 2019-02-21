from . import ast
from . import lexer
from . import types
from mtots import test
from mtots.text import base
from mtots.text.combinator import All
from mtots.text.combinator import Any
from mtots.text.combinator import AnyTokenBut
from mtots.text.combinator import Forward
from mtots.text.combinator import Peek
from mtots.text.combinator import Token

# Useful for skipping blocks of code
# for the header parser
blob = Forward(lambda: Any(
    All('{', blob.repeat(), '}'),
    AnyTokenBut('{', '}'),
))

# These are modifiers that affect the type of a function
# i.e. does the type of the function pointer need to know
# this about the function it's pointinng to?
func_decl_modifier = Any(
    # Windows calling conventions
    Token('ID', '__cdecl'),
    Token('ID', '__clrcall'),
    Token('ID', '__stdcall'),
    Token('ID', '__fastcall'),
    Token('ID', '__thiscall'),
    Token('ID', '__vectorcall'),
)

# These are modifiers that affect the definition of a function
# e.g. if a function is declared static, the function definition
# must handle it accordingly, but a pointer to that function does
# not need to know.
func_defn_modifier = Any(
    'static',
    func_decl_modifier,
)

type_ref = Forward(lambda: Any(
    All('*', type_ref).map(lambda args: types.PointerType(args[1])),
    All('const', type_ref).map(lambda args: types.ConstType(args[1])),
    All(
        '(',                                           # 0
            type_ref.join(','),                        # 1: param types
            All(',', '...').optional(),                # 2: vararg
        ')',                                           # 3
        Any(
            All('[', func_decl_modifier.repeat(), ']')
                .map(lambda args: args[1])
                .map(sorted),
            All(),
        ),                                             # 4: attributes
        type_ref,                                      # 5: return type
    ).map(lambda args: types.FunctionType(
        ptypes=args[1],
        varargs=bool(args[2]),
        attrs=args[4],
        rtype=args[5],
    )),

    # Primitive types
    All('void').map(lambda x: types.VOID),
    All('char').map(lambda x: types.CHAR),
    All('signed', 'char').map(lambda x: types.SIGNED_CHAR),
    All('unsigned', 'char').map(lambda x: types.UNSIGNED_CHAR),
    All('short').map(lambda x: types.SHORT),
    All('unsigned', 'short').map(lambda x: types.UNSIGNED_SHORT),
    All('int').map(lambda x: types.INT),
    All('unsigned', 'int').map(lambda x: types.UNSIGNED_INT),
    All('long', 'long').map(lambda x: types.LONG_LONG),
    All('unsigned', 'long', 'long').map(lambda x: types.UNSIGNED_LONG_LONG),
    All('long').map(lambda x: types.LONG),
    All('unsigned', 'long').map(lambda x: types.UNSIGNED_LONG),
    All('float').map(lambda x: types.FLOAT),
    All('double').map(lambda x: types.DOUBLE),
    All('long', 'double').map(lambda x: types.LONG_DOUBLE),

    # Struct and typedef'd types
    Any('ID')
        .map(types.NamedType)
        .recover(lambda mr: base.Failure(mr.mark, 'Expected type')),
))

struct_decl = All(
    'struct', 'ID', ';',
).fatmap(lambda m: ast.StructDeclaration(
    mark=m.mark,
    name=m.value[1],
))

struct_field = All(
    'ID', type_ref, ';',
).fatmap(lambda m: ast.Field(
    mark=m.mark,
    name=m.value[0],
    type=m.value[1],
))

struct_defn = All(
    'struct',                                # 0
    'ID',                                    # 1: name
    Any('native').optional().map(bool),      # 2: native
    '{',                                     # 3
    struct_field.repeat(),                   # 4: fields
    '}',                                     # 5
).fatmap(lambda m: ast.StructDefinition(
    mark=m.mark,
    name=m.value[1],
    native=m.value[2],
    fields=m.value[4],
))

func_param = (
    All('ID', type_ref)
        .fatmap(lambda m: ast.Param(
            mark=m.mark,
            name=m.value[0],
            type=m.value[1],
        ))
)

func_params = All(
    '(',
    func_param.join(','),
    Any(
        All(',', '...').map(lambda x: True),
        Any(',').optional().map(lambda x: False),
    ),
    ')',
).map(lambda args: {
    'params': args[1],
    'varargs': args[2],
})

func_modifiers = Any(
    All(
        '[',
        func_defn_modifier.repeat().map(sorted),
        ']',
    ).map(lambda args: args[1]),

    # If no modifiers are specified, just return an empty list
    All(),
)

func_proto = All(
    'def',           # 0
    'ID',            # 1: name
    func_params,     # 2: parameters
    func_modifiers,  # 3: function modifiers/attributes
    type_ref,        # 4: return type
).fatmap(lambda m: ast.FunctionDeclaration(
    mark=m.mark,
    name=m.value[1],
    params=m.value[2]['params'],
    varargs=m.value[2]['varargs'],
    attrs=m.value[3],
    rtype=m.value[4],
))

func_decl = All(func_proto, ';').map(lambda args: args[0])


@test.case
def test_blob():
    def parse(s):
        return (
            All(blob.repeat(), Peek('EOF'))
                .map(lambda args: args[0])
                .parse(lexer.lex_string(s))
        )

    blob_result = parse(r"""
    # Hi, this is some code
    import <stdio.h>

    def main() int {
        printf("Hello world!\n");
        return 0;
    }
    """)

    test.equal(
        blob_result,
        base.Success(
            None,
            [
                'import', '<', 'stdio', '.', 'h', '>',
                'def', 'main', '(', ')', 'int',
                    ['{', [
                        'printf', '(', 'Hello world!\n', ')', ';',
                        'return', 0, ';',
                    ], '}'],
            ],
        ),
    )


@test.case
def test_type_ref():
    def parse(s):
        return (
            All(type_ref, Peek('EOF'))
                .map(lambda args: args[0])
                .parse(lexer.lex_string(s))
        )

    test.equal(parse('int'), base.Success(None, types.INT))
    test.equal(parse('void'), base.Success(None, types.VOID))
    test.equal(
        parse('*void'),
        base.Success(None, types.PointerType(types.VOID)),
    )
    test.equal(
        parse('Foo'),
        base.Success(None, types.NamedType('Foo')),
    )
    test.equal(
        parse('()int'),
        base.Success(None, types.FunctionType(
            ptypes=[],
            varargs=False,
            attrs=[],
            rtype=types.INT,
        ))
    )
    test.equal(
        parse('(int)[__cdecl]double'),
        base.Success(None, types.FunctionType(
            ptypes=[types.INT],
            varargs=False,
            attrs=['__cdecl'],
            rtype=types.DOUBLE,
        ))
    )
    test.equal(
        parse('while'),
        base.Failure(None, 'Expected type'),
    )


@test.case
def test_struct_decl():
    def parse(s):
        return (
            All(struct_decl, Peek('EOF'))
                .map(lambda args: args[0])
                .parse(lexer.lex_string(s))
        )

    test.equal(
        parse('struct Foo;'),
        base.Success(
            None,
            ast.StructDeclaration(None, 'Foo'),
        ),
    )

    test.equal(
        parse('struct Foo'),
        base.Failure(None, 'Expected ; but got EOF'),
    )


@test.case
def test_struct_defn():
    def parse(s):
        return (
            All(struct_defn, Peek('EOF'))
                .map(lambda args: args[0])
                .parse(lexer.lex_string(s))
        )

    test.equal(
        parse("""
        struct Foo {
            b Bar;
            x *int;
        }
        """),
        base.Success(None, ast.StructDefinition(
            mark=None,
            name='Foo',
            native=False,
            fields=[
                ast.Field(
                    mark=None,
                    name='b',
                    type=types.NamedType('Bar'),
                ),
                ast.Field(
                    mark=None,
                    name='x',
                    type=types.PointerType(types.INT),
                ),
            ],
        )),
    )


    test.equal(
        parse("""
        struct Foo native {
            b Bar;
            x *int;
        }
        """),
        base.Success(None, ast.StructDefinition(
            mark=None,
            name='Foo',
            native=True,
            fields=[
                ast.Field(
                    mark=None,
                    name='b',
                    type=types.NamedType('Bar'),
                ),
                ast.Field(
                    mark=None,
                    name='x',
                    type=types.PointerType(types.INT),
                ),
            ],
        )),
    )


@test.case
def test_func_decl():
    def parse(s):
        return (
            All(func_decl, Peek('EOF'))
                .map(lambda args: args[0])
                .parse(lexer.lex_string(s))
        )

    # Test simple example
    test.equal(
        parse('def foo(b Bar, z int) void;'),
        base.Success(
            None,
            ast.FunctionDeclaration(
                mark=None,
                name='foo',
                params=[
                    ast.Param(None, 'b', types.NamedType('Bar')),
                    ast.Param(None, 'z', types.INT),
                ],
                varargs=False,
                attrs=[],
                rtype=types.VOID,
            ),
        ),
    )

    # Test attrs entry
    test.equal(
        parse('def foo(b Bar, z int) [static] void;'),
        base.Success(
            None,
            ast.FunctionDeclaration(
                mark=None,
                name='foo',
                params=[
                    ast.Param(None, 'b', types.NamedType('Bar')),
                    ast.Param(None, 'z', types.INT),
                ],
                varargs=False,
                attrs=['static'],
                rtype=types.VOID,
            ),
        ),
    )

    # Test vararg and empty attrs
    test.equal(
        parse('def foo(b Bar, z int, ...) [] void;'),
        base.Success(
            None,
            ast.FunctionDeclaration(
                mark=None,
                name='foo',
                params=[
                    ast.Param(None, 'b', types.NamedType('Bar')),
                    ast.Param(None, 'z', types.INT),
                ],
                varargs=True,
                attrs=[],
                rtype=types.VOID,
            ),
        ),
    )
