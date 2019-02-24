from . import ast
from . import errors
from . import lexer
from . import types
from .scopes import Scope
from mtots import test
from mtots.text import base
from mtots.text.combinator import All
from mtots.text.combinator import Any
from mtots.text.combinator import AnyTokenBut
from mtots.text.combinator import Forward
from mtots.text.combinator import Peek
from mtots.text.combinator import Token
import os

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

simple_type_ref = Any(
    Any('ID').map(types.NamedType),
    primitive_type_ref,
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

    All('const', simple_type_ref)
        .map(lambda args: types.ConstType(args[1])),

    simple_type_ref
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
    All(type_ref, Any('ID').required())
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

func_defn = Forward(lambda: All(
    func_proto,
    block,
)).fatmap(lambda m: ast.FunctionDefinition(
    mark=m.mark,
    rtype=m.value[0].rtype,
    name=m.value[0].name,
    attrs=m.value[0].attrs,
    params=m.value[0].params,
    varargs=m.value[0].varargs,
    body=m.value[1],
))


def source_callback(m):
    imports = m.value.imports
    decls = m.value.decls
    scope = Scope(None)
    for imp in imports:
        if isinstance(imp, ast.AbsoluteImport):
            for decl in load_header(imp.path).decls:
                scope.set(decl.name, decl, [])
    for decl in decls:
        scope.set(decl.name, decl, [])
    for decl in decls:
        if isinstance(decl, ast.FunctionDefinition):
            decl.body.annotate(scope)
    return m.value

    return source_callback

source = Forward(lambda: All(
    import_stmt.repeat(),
    Any(
        struct_decl,
        struct_defn,
        func_decl,
        func_defn,
    ).repeat(),
)).fatmap(lambda m: ast.Source(
    mark=m.mark,
    imports=m.value[0],
    decls=m.value[1],
)).fatmap(source_callback)


expression = Forward(lambda: Any(
    function_call,
    Any('STR').fatmap(lambda m: ast.StringLiteral(
        mark=m.mark,
        value=m.value,
    )),
))

statement = Forward(lambda: Any(
    block,
    expression_statement,
))

block = All('{', statement.repeat(), '}').fatmap(lambda m: ast.Block(
    mark=m.mark,
    stmts=m.value[1],
))

expression_statement = All(
    expression, ';',
).fatmap(lambda m: ast.ExpressionStatement(
    mark=m.mark,
    expr=m.value[0],
))

call_args = All(
    '(',
    expression.join(','),
    Any(',').optional(),
    ')',
).map(lambda args: args[1])

function_call = All(
    'ID', call_args,
).fatmap(lambda m: ast.FunctionCall(
    mark=m.mark,
    name=m.value[0],
    args=m.value[1],
))


_source_root = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'root',
)


def _make_exports():
    def _import_path_to_file_path(import_path):
        return os.path.join(
            _source_root,
            import_path.replace('.', os.path.sep) + '.nc',
        )


    def _make_base_source(data, file_path, import_path):
        return base.Source(
            data=data,
            path=file_path,
            metadata={
                'import_path': import_path,
            }
        )


    def _load_base_source(import_path):
        file_path = _import_path_to_file_path(import_path)
        with open(file_path) as f:
            data = f.read()
        return _make_base_source(
            data=data,
            file_path=file_path,
            import_path=import_path,
        )


    def parse_header_source(source):
        return _parse_pattern(pattern=header, source=source)


    def _load_header_without_cache(import_path):
        return parse_header_source(_load_base_source(import_path))


    def _parse_pattern(pattern, source):
        tokens = lexer.lex(source)
        match_result = pattern.parse(tokens)
        if not match_result:
            raise match_result.to_error()
        return match_result.value


    def parse_header(data, file_path='<string>', import_path='__main__'):
        return parse_header_source(_make_base_source(
            data=data,
            file_path=file_path,
            import_path=import_path,
        ))


    _header_cache = {}


    def load_header(import_path):
        if import_path not in _header_cache:
            _header_cache[import_path] = _load_header_without_cache(import_path)
        return _header_cache[import_path]


    def parse_source(data, file_path='<string>', import_path='__main__'):
        return _parse_source_source(_make_base_source(
            data=data,
            file_path=file_path,
            import_path=import_path,
        ))


    def parse_source_source(base_source):
        return _parse_pattern(pattern=source, source=base_source)


    def load_source(import_path):
        base_source = _load_base_source(import_path)
        return parse_source_source(
            data=base_source.data,
            path=base_source.path,
        )

    return {
        'load_source': load_source,
        'load_header': load_header,
        'parse_source': parse_source,
        'parse_header': parse_header,
    }


_exports = _make_exports()

# Functions that accept an import_path
load_source = _exports['load_source']
load_header = _exports['load_header']

# Functions that accept 'data' string, and optionally
# 'file_path' and 'import_path'
parse_source = _exports['parse_source']
parse_header = _exports['parse_header']


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
        void print(char* x);
        """),
        base.Success(
            None,
            ast.Header(
                None,
                imports=[ast.AngleBracketImport(None, path='stdio.h')],
                decls=[
                    ast.FunctionDeclaration(
                        None,
                        rtype=types.INT,
                        name='main',
                        params=[],
                        varargs=False,
                        attrs=[],
                    ),
                    ast.FunctionDeclaration(
                        None,
                        rtype=types.VOID,
                        name='print',
                        attrs=[],
                        params=[
                            ast.Param(
                                None,
                                type=types.PointerType(types.CHAR),
                                name='x',
                            ),
                        ],
                        varargs=False,
                    ),
                ],
            ),
        ),
    )


@test.case
def test_source():
    def parse(s):
        return (
            All(source, Peek('EOF'))
                .map(lambda args: args[0])
                .parse(lexer.lex_string(s))
        )

    test.equal(
        parse("""
        int main() {
            print("Hello world!");
        }
        void print(const char* x);
        """),
        base.Success(
            None,
            ast.Source(
                None,
                imports=[],
                decls=[
                    ast.FunctionDefinition(
                        None,
                        name='main',
                        rtype=types.INT,
                        attrs=[],
                        params=[],
                        varargs=False,
                        body=ast.Block(
                            None,
                            stmts=[
                                ast.ExpressionStatement(
                                    None,
                                    expr=ast.FunctionCall(
                                        None,
                                        name='print',
                                        args=[
                                            ast.StringLiteral(
                                                None,
                                                value='Hello world!',
                                            ),
                                        ],
                                    ),
                                ),
                            ],
                        ),
                    ),
                    ast.FunctionDeclaration(
                        None,
                        name='print',
                        rtype=types.VOID,
                        attrs=[],
                        params=[
                            ast.Param(
                                None,
                                name='x',
                                type=types.PointerType(
                                    types.ConstType(types.CHAR),
                                ),
                            ),
                        ],
                        varargs=False,
                    ),
                ],
            ),
        ),
    )


@test.case
def test_import():
    def parse(s):
        return (
            All(source, Peek('EOF'))
                .map(lambda args: args[0])
                .parse(lexer.lex_string(s))
        )

    error_message = r"""'printf' is not defined
on line 3
            printf("Hello world!\n");
            *"""

    @test.throws(errors.MissingReference)
    def missing_reference():
        parse(r"""
        int main() {
            printf("Hello world!\n");
        }
        """)

    test.equal(
        parse(r"""
        import stdio
        int main() {
            printf("Hello world!\n");
        }
        """),
        base.Success(
            None,
            ast.Source(
                None,
                imports=[
                    ast.AbsoluteImport(None, path='stdio'),
                ],
                decls=[
                    ast.FunctionDefinition(
                        None,
                        name='main',
                        rtype=types.INT,
                        attrs=[],
                        params=[],
                        varargs=False,
                        body=ast.Block(
                            None,
                            stmts=[
                                ast.ExpressionStatement(
                                    None,
                                    expr=ast.FunctionCall(
                                        None,
                                        name='printf',
                                        args=[
                                            ast.StringLiteral(
                                                None,
                                                value='Hello world!\n',
                                            ),
                                        ],
                                    ),
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        ),
    )
