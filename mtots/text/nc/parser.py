"""
Full parsing is split into 3 phases:

    * phase 1 (forward header):
        Extract:
            * what other files are imported
            * the typenames declared in the given
              text, and what kind of type they are
              (e.g. class or struct or native typedef)
    * phase 2 (header):
        Using result from phase 1, parse everything but function bodies
    * phase 3 (full source):
        Using result from phase 2, fully parse everything

# TODO: Create the parsers inside closures for phase 2 and phase 3
# so that the parser can capture the output of previous phases
# easily

"""
from . import ast
from . import errors
from . import lexer
from mtots import test
from mtots.text import base
from mtots.text.combinator import All
from mtots.text.combinator import Any
from mtots.text.combinator import AnyTokenBut
from mtots.text.combinator import Forward
from mtots.text.combinator import Peek
from mtots.text.combinator import Token
import os
import typing


# Useful for skipping blocks of code
# for the header parser
blob = Forward(lambda: Any(
    brace_blob,
    AnyTokenBut('{', '}'),
))

brace_blob = All('{', blob.repeat(), '}')

include_stmt = Any(
    # C header imports with angle brackets, e.g.
    # import <stdio.h>
    All(
        'import',
        All('<', AnyTokenBut('>').repeat(), '>')
            .map(lambda args: ''.join(map(str, args[1]))),
    ).fatmap(lambda m: ast.Include(
        mark=m.mark,
        quotes=False,
        path=m.value[1],
    )),

    # C header imports, quoted. e.g.
    # import "foo.h"
    All('import', 'STR').fatmap(lambda m: ast.QuoteImport(
        mark=m.mark,
        quotes=True,
        path=m.value[1],
    )),
)

import_stmt = All(
    'import',
    All(
        'ID',
        All('.', 'ID').map(lambda args: args[1]).repeat(),
    ).map(lambda args: '.'.join([args[0]] + args[1])),
).fatmap(lambda m: ast.Import(
    mark=m.mark,
    path=m.value[1],
))

native_typedef = All(
    'native', 'typedef', 'ID',
).fatmap(lambda m: ast.NativeTypedef(
    mark=m.mark,
    name=m.value[2],
))

phase1_struct_def = All(
    'struct', 'ID',
).fatmap(lambda m: ast.StructDefinition(
    mark=m.mark,
    native=None,
    name=m.value[1],
    fields=None,
))


class Phase1(typing.NamedTuple):
    imports: typing.Tuple[ast.Import, ...]
    types: typing.Dict[str, typing.Union[
        ast.StructDefinition,
        ast.NativeTypedef,
    ]]


def _phase1_callback(m):
    imports = []
    types = {}
    for node in m.value:
        if isinstance(node, ast.Import):
            imports.append(node)
        elif isinstance(node, (ast.StructDefinition, ast.NativeTypedef)):
            types[node.name] = node
        else:
            raise TypeError(node)
    return Phase1(imports=imports, types=types)


phase1_parser = Any(
    All(import_stmt),
    All(phase1_struct_def),
    All(native_typedef),
    blob.map(lambda x: []),
).repeat().flatten().fatmap(_phase1_callback)


def _parse_pattern(pattern, data, file_path, import_path):
    source = base.Source(data=data, path=file_path)
    tokens = lexer.lex(source)
    match_result = (
        All(pattern, Peek('EOF'))
            .map(lambda args: args[0])
            .parse(tokens)
    )
    if not match_result:
        raise match_result.to_error()
    return match_result.value


def parse_phase1(data, *, file_path='<string>', import_path='__main__'):
    return _parse_pattern(
        pattern=phase1_parser,
        data=data,
        file_path=file_path,
        import_path=import_path,
    )


@test.case
def test_phase1():
    test.equal(
        parse_phase1("""
            import <stdio.h>
            import a.b.c
            import x

            struct Foo {
                Foo foo;
            }

            int main() {
                return 0;
            }
        """),
        Phase1(
            imports=[
                ast.Import(None, path='a.b.c'),
                ast.Import(None, path='x'),
            ],
            types={
                'Foo': ast.StructDefinition(
                    None,
                    native=None,
                    name='Foo',
                    fields=None),
            },
        ),
    )
