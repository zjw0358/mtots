from mtots import test
from mtots.text import base
from mtots.text.combinator import All, Any, Forward, Success
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

package_declaration = All(
    'package',
    All(
        'ID',
        All('.', 'ID')
            .map(lambda args: args[1])
            .repeat()
            .map('.'.join),
    ).map('.'.join),
    ';',
).xmap(lambda result: Success(
    result.mark,
    ast.PackageDeclaration(
        mark=result.mark,
        name=result.value[1],
    ),
))



@test.case
def test_package_declaration():
    result = package_declaration.parse(lexer.lex_string('package a.b.c.dd;'))
    test.equal(
        result,
        Success(result.mark, ast.PackageDeclaration(result.mark, 'a.b.c.dd')),
    )

