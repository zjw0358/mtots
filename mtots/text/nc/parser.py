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
    brace_blob,
    AnyTokenBut('{', '}'),
))

brace_blob = All('{', blob.repeat(), '}')

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

primitive_type_ref = Any(
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
)

type_ref = Forward(lambda: Any(
    All(type_ref, '*').map(lambda args: types.PointerType(args[0])),
    All(type_ref, 'const').map(lambda args: types.ConstType(args[0])),
    All(
        type_ref,                                      # 0: return type
        Any(
            All('[', func_decl_modifier.repeat(), ']')
                .map(lambda args: args[1])
                .map(sorted),
            All(),
        ),                                             # 1: attributes
        '(',                                           # 2
            type_ref.join(','),                        # 3: param types
            All(',', '...').optional(),                # 4: vararg
        ')',                                           # 5
    ).map(lambda args: types.FunctionType(
        rtype=args[0],
        attrs=args[1],
        ptypes=args[3],
        varargs=bool(args[4]),
    )),

    All('const', primitive_type_ref)
        .map(lambda args: types.ConstType(args[1])),

    primitive_type_ref,

    # Struct and typedef'd types
    Any('ID')
        .map(types.NamedType)
        .recover(lambda mr: base.Failure(mr.mark, 'Expected type')),
))

import_stmt = Any(
    # C header imports with angle brackets, e.g.
    # import <stdio.h>
    All(
        'import',
        All('<', AnyTokenBut('>').repeat(), '>')
            .map(lambda args: ''.join(map(str, args[1]))),
    ).fatmap(lambda m: ast.AngleBracketImport(
        mark=m.mark,
        path=m.value[1],
    )),

    # C header imports, quoted. e.g.
    # import "foo.h"
    All('import', 'STR').fatmap(lambda m: ast.QuoteImport(
        mark=m.mark,
        path=m.value[1],
    )),

    # Declare dependency on another NC file. e.g.
    # import some_package.some_filename
    All(
        'import',
        Any('ID').join('.').map('.'.join),
    ).fatmap(lambda m: ast.AbsoluteImport(
        mark=m.mark,
        path=m.value[1],
    )),
)

struct_decl = All(
    'struct', 'ID', ';',
).fatmap(lambda m: ast.StructDeclaration(
    mark=m.mark,
    name=m.value[1],
))

struct_field = All(
    type_ref, 'ID', ';',
).fatmap(lambda m: ast.Field(
    mark=m.mark,
    type=m.value[0],
    name=m.value[1],
))

struct_defn = All(
    Any('native').optional().map(bool),      # 0: native
    'struct',                                # 1
    'ID',                                    # 2: name
    '{',                                     # 3
    struct_field.repeat(),                   # 4: fields
    '}',                                     # 5
).fatmap(lambda m: ast.StructDefinition(
    mark=m.mark,
    native=m.value[0],
    name=m.value[2],
    fields=m.value[4],
))

func_param = (
    All(type_ref, 'ID')
        .fatmap(lambda m: ast.Param(
            mark=m.mark,
            type=m.value[0],
            name=m.value[1],
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
    type_ref,        # 0: return type
    'ID',            # 1: name
    func_modifiers,  # 2: function modifiers/attributes
    func_params,     # 3: parameters
).fatmap(lambda m: ast.FunctionDeclaration(
    mark=m.mark,
    rtype=m.value[0],
    name=m.value[1],
    attrs=m.value[2],
    params=m.value[3]['params'],
    varargs=m.value[3]['varargs'],
))

func_decl = All(func_proto, ';').map(lambda args: args[0])

# Header parser,
# Skips over function bodies, but doesn't need any external context
# to parse a file.
header = All(
    import_stmt.repeat(),
    Any(
        struct_decl,
        struct_defn,
        func_decl,
        All(func_proto, brace_blob).map(lambda args: args[0]),
    ).repeat(),
).fatmap(lambda m: ast.Header(
    mark=m.mark,
    imports=m.value[0],
    decls=m.value[1],
))

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
        parse('void*'),
        base.Success(None, types.PointerType(types.VOID)),
    )
    test.equal(
        parse('Foo'),
        base.Success(None, types.NamedType('Foo')),
    )
    test.equal(
        parse('int()'),
        base.Success(None, types.FunctionType(
            ptypes=[],
            varargs=False,
            attrs=[],
            rtype=types.INT,
        ))
    )
    test.equal(
        parse('double[__cdecl](int)'),
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
def test_import_stmt():
    def parse(s):
        return (
            All(import_stmt.repeat(), Peek('EOF'))
                .map(lambda args: args[0])
                .parse(lexer.lex_string(s))
        )

    test.equal(
        parse("""
        import <stdio.h>
        import "stdlib.h"
        import a.b.c
        """),
        base.Success(
            None,
            [
                ast.AngleBracketImport(None, path='stdio.h'),
                ast.QuoteImport(None, path='stdlib.h'),
                ast.AbsoluteImport(None, path='a.b.c'),
            ],
        ),
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
            Bar b;
            int* x;
        }
        """),
        base.Success(None, ast.StructDefinition(
            mark=None,
            native=False,
            name='Foo',
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
        native struct Foo {
            Bar b;
            int* x;
        }
        """),
        base.Success(None, ast.StructDefinition(
            mark=None,
            native=True,
            name='Foo',
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
        parse('void foo(Bar b, int z);'),
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
        parse('void foo[static](Bar b, int z);'),
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
        parse('void foo[](Bar b, int z, ...);'),
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


@test.case
def test_header():
    def parse(s):
        return (
            All(header, Peek('EOF'))
                .map(lambda args: args[0])
                .parse(lexer.lex_string(s))
        )

    test.equal(
        parse("""
        import <stdio.h>

        int main() {
            print("Hello world!");
        }
        """),
        base.Success(
            None,
            ast.Header(
                None,
                imports=[ast.AngleBracketImport(None, path='stdio.h')],
                decls=[
                    ast.FunctionDeclaration(
                        None,
                        name='main',
                        params=[],
                        varargs=False,
                        attrs=[],
                        rtype=types.NamedType(name='int')),
                ],
            ),
        ),
    )
