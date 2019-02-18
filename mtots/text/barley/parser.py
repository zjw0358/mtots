from . import ast
from . import lexer
from mtots import test
from mtots.text import base


@base.Parser.new
def parser(builder):

    @builder.add_rule
    def module(ctx, scope):
        mark = ctx.mark
        imports = []
        definitions = []
        while not ctx.at('EOF'):
            if ctx.consume('NEWLINE'):
                pass
            elif ctx.at('import'):
                imports.append(import_declaration(ctx, scope))
            elif ctx.at('struct'):
                definitions.append(struct_declaration(ctx, scope))
            else:
                definitions.append(function_declaration(ctx, scope))
        return ast.Module(
            name=scope['@module_name'],
            mark=mark,
            imports=imports,
            definitions=definitions,
        )

    def import_declaration(ctx, scope):
        mark = ctx.mark
        ctx.expect('import')
        parts = [ctx.expect('ID').value]
        while ctx.consume('.'):
            parts.append(ctx.expect('ID').value)
        if ctx.consume('as'):
            alias = ctx.expect('ID').value
        else:
            alias = parts[-1]
        ctx.expect('NEWLINE')
        module_name = '.'.join(parts)
        if alias in scope['@import_table']:
            raise base.Error(
                [ctx.mark],
                f'Import alias {alias} already used',
            )
        scope['@import_table'][alias] = module_name
        return ast.Import(
            mark=mark,
            name=module_name,
            alias=alias,
        )

    primitive_type_ref_token_types = ('void', 'int', 'double', 'string')

    def type_ref(ctx, scope):
        if ctx.consume('('):
            subtypes = []
            while not ctx.consume(')'):
                subtypes.append(type_ref(ctx, scope))
                if not ctx.consume(','):
                    ctx.expect(')')
                    break
            ret = ast.TupleType(subtypes)
        elif any(map(ctx.at, primitive_type_ref_token_types)):
            ret = ast.SimpleType(ctx.gettok().type)
        elif ctx.at('ID'):
            first_name = ctx.expect('ID').value
            if ctx.consume('.'):
                member_name = ctx.expect('ID').value
                if first_name not in scope['@import_table']:
                    raise base.Error(
                        [ctx.mark],
                        f'{first_name} is not an imported module name',
                    )
                module_name = scope['@import_table'][first_name]
            else:
                member_name = first_name
                module_name = scope['@module_name']
            full_name = f'{module_name}#{member_name}'
            ret = ast.StructType(full_name)
        else:
            raise base.Error([ctx.mark], 'Expected type reference')

        while True:
            if ctx.consume('['):
                ctx.expect(']')
                ret = ast.ListType(ret)
            elif ctx.consume('('):
                argtypes = []
                while not ctx.consume(')'):
                    argtypes.append(type_ref(ctx, scope))
                    if not ctx.consume(','):
                        ctx.expect(')')
                        break
                ret = ast.FunctionType(ret, argtypes)
            else:
                break

        return ret

    def struct_declaration(ctx, scope):
        mark = ctx.mark
        ctx.expect('struct')
        name = ctx.expect('ID').value
        native = bool(ctx.consume('native'))
        if native:
            fields = None
        else:
            fields = []
            ctx.consume('NEWLINE')
            ctx.expect('INDENT')
            while not ctx.consume('DEDENT'):
                if ctx.consume('pass'):
                    ctx.expect('NEWLINE')
                elif ctx.consume('NEWLINE'):
                    pass
                else:
                    field_mark = ctx.mark
                    field_type = type_ref(ctx, scope)
                    field_name = ctx.expect('ID').value
                    fields.append(ast.Field(
                        mark=field_mark,
                        type=field_type,
                        name=field_name,
                    ))
        return ast.Struct(
            mark=mark,
            native=native,
            module_name=scope['@module_name'],
            short_name=name,
            fields=fields,
        )

    def function_declaration(ctx, scope):
        mark = ctx.mark
        return_type = type_ref(ctx, scope)
        name = ctx.expect('ID').value
        params = []
        ctx.expect('(')
        while not ctx.consume(')'):
            param_mark = ctx.mark
            param_type = type_ref(ctx, scope)
            param_name = ctx.expect('ID').value
            params.append(ast.Parameter(param_mark, param_type, param_name))
            if not ctx.consume(','):
                ctx.expect(')')
                break
        native = bool(ctx.consume('native'))
        ctx.expect('NEWLINE')
        if native:
            body = None
            if ctx.at('INDENT'):
                raise base.Error(
                    [ctx.mark],
                    'Native functions cannot have function bodies',
                )
        else:
            body = block(ctx, scope)
        return ast.FunctionDefinition(
            module_name=scope['@module_name'],
            mark=mark,
            native=native,
            return_type=return_type,
            short_name=name,
            parameters=params,
            body=body,
        )

    def block(ctx, scope):
        mark = ctx.mark
        ctx.consume('NEWLINE')
        ctx.expect('INDENT')
        stmts = []
        while not ctx.consume('DEDENT'):
            stmts.extend(statement(ctx, scope))
        return ast.Block(
            mark=mark,
            statements=stmts,
        )

    def statement(ctx, scope):
        if ctx.consume('NEWLINE'):
            return []
        elif ctx.consume('pass'):
            ctx.expect('NEWLINE')
            return []
        elif ctx.at('INDENT'):
            return [block(ctx, scope)]
        else:
            raise base.Error([ctx.mark], 'Expected statement')


def _parse(s):
    scope = {
        '@module_name': 'sample.module',
        '@import_table': {},
    }
    tokens = lexer.lex_string(s)
    return parser.parse('module', tokens, rule_args=[scope])


@test.case
def test_simple_case():
    print(_parse("""
import io

struct Foo native

struct Bar
    int a
    string[] s
    Bar bar
    Foo foo
    io.File file

int foo(int a) native

int main()
    pass
"""))
