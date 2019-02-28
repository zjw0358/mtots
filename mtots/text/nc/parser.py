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
from mtots.util import Scope
import os
import typing


_source_root = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'root',
)


def _import_path_to_file_path(import_path):
    return os.path.join(
        _source_root,
        import_path.replace('.', os.path.sep) + '.nc',
    )


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


class Phase1(typing.NamedTuple):
    imports: typing.Tuple[ast.Import, ...]
    types: typing.Dict[str, typing.Union[
        ast.StructDefinition,
        ast.NativeTypedef,
    ]]


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


def _make_phase1_parse_functions():

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

    # Useful for skipping blocks of code
    blob = Forward(lambda: Any(
        brace_blob,
        AnyTokenBut('{', '}'),
    ))

    brace_blob = All('{', blob.repeat(), '}')

    phase1_struct_def = All(
        'struct', 'ID',
    ).fatmap(lambda m: ast.StructDefinition(
        mark=m.mark,
        native=None,
        name=m.value[1],
        fields=None,
    ))

    phase1_parser = Any(
        All(import_stmt),
        All(phase1_struct_def),
        All(native_typedef),
        blob.map(lambda x: []),
    ).repeat().flatten().fatmap(_phase1_callback)

    def parse_phase1(data, *, file_path='<string>', import_path='__main__'):
        return _parse_pattern(
            pattern=phase1_parser,
            data=data,
            file_path=file_path,
            import_path=import_path,
        )


    def read_phase1(file_path, *, import_path='__main__'):
        with open(file_path) as f:
            data = f.read()
        return parse_phase1(
            data,
            file_path=file_path,
            import_path=import_path,
        )

    _phase1_cache = {}


    def load_phase1(import_path):
        if import_path not in _phase1_cache:
            file_path = _import_path_to_file_path(import_path)
            _phase1_cache[import_path] = read_phase1(
                file_path,
                import_path=import_path,
            )

    return (
        parse_phase1,
        read_phase1,
        load_phase1,
    )

parse_phase1, read_phase1, load_phase1 = _make_phase1_parse_functions()


def _update_scope(scope, other_scope):
    for key in other_scope:
        if key in scope:
            raise base.Error(
                [scope[key].mark, other_scope[key].mark],
                f'Duplicate definition {key}'
            )
        scope[key] = other_scope[key]


def new_phase2_parser(phase1: Phase1):
    type_dict = {}
    for imp in phase1.imports:
        _update_scope(type_dict, load_phase1(imp.path).types)
    _update_scope(type_dict, phase1.types)


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
