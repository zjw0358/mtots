from mtots import test
from mtots.text import base
from mtots.text.combinator import All
from mtots.text.combinator import Any
from mtots.text.combinator import AnyTokenBut
from mtots.text.combinator import Forward
from mtots.text.combinator import Success
from mtots.text.java import ast
from mtots.text.java import lexer


compilation_unit = Forward(lambda:
    All(
        package_declaration,
        import_declaration.repeat(),
        type_declaration.repeat(),
        'EOF',
    ).map(lambda args: ast.CompilationUnit(
        package_declaration=args[0],
        import_declarations=args[1],
        type_declarations=args[2],
    ))
)

qualified_pattern = All(
    'ID',
    All('.', 'ID')
        .map(''.join)
        .repeat()
        .map(''.join)
).map(''.join)

package_declaration = All(
    'package',
    qualified_pattern,
    ';',
).fatmap(lambda result: ast.PackageDeclaration(
    mark=result.mark,
    name=result.value[1],
))

import_declaration = All(
    'import',
    Any('static').optional(),
    qualified_pattern,
    ';',
).fatmap(lambda result: ast.ImportDeclaration(
    mark=result.mark,
    static=bool(result.value[1]),
    pattern=result.value[2],
))

type_reference = Forward(lambda: Any('ID'))

type_declaration = Forward(lambda: Any(
    class_declaration,
    # interface_declaration,
    # enum_declaration,
    # annotation_declaration,
))

extends_class = All(
    'extends',
    type_reference,
).map(lambda args: args[1])

implements_interface = All(
    'implements',
    type_reference.repeat(),
).map(lambda args: args[1])

class_declaration = Forward(lambda: All(
    modifier.repeat(),
    'class',
    'ID',
    extends_class.optional(),
    implements_interface.repeat().map(lambda args:
        [x for seq in args for x in seq]
    ),
    block,  # body
))

modifier = Forward(lambda: Any(
    simple_modifier,
    # annotation,  # TODO
))

# Combines modifiers for all kinds of things (e.g. classes, interfaces,
# methods, fields, etc.)
simple_modifier = Any(
    'abstract',
    'final',
    'native',
    'private ',
    'private',
    'protected',
    'public',
    'static',
    'strictfp',
    'synchronized',
)

blob = Forward(lambda: Any(
    AnyTokenBut('{', '}'),
    All('{', blob.repeat(), '}'),
).fatmap(lambda result: result.mark))

block = blob.map(ast.Block)


@test.case
def test_package_declaration():
    result = package_declaration.parse(lexer.lex_string('package a.b.c.dd;'))
    test.equal(
        result,
        Success(result.mark, ast.PackageDeclaration(result.mark, 'a.b.c.dd')),
    )


@test.case
def test_package_declaration():
    result = import_declaration.parse(lexer.lex_string('import a.b.c.dd;'))
    test.equal(
        result,
        Success(
            result.mark,
            ast.ImportDeclaration(result.mark, False, 'a.b.c.dd'),
        ),
    )

    result = import_declaration.parse(lexer.lex_string(
        'import static a.b.c.dd;',
    ))
    test.equal(
        result,
        Success(
            result.mark,
            ast.ImportDeclaration(result.mark, True, 'a.b.c.dd'),
        ),
    )

