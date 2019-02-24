"""C codegen
"""
from . import ast
from . import parser
from . import types
from mtots import test
from mtots import util


@util.multimethod(1)
def declare(builder):

    @builder.on(types._PrimitiveType)
    def builder(type, name):
        return f'{type.name} {name}'

    @builder.on(types.NamedType)
    def builder(type, name):
        return f'{type.name} {name}'

    @builder.on(ast.FunctionDeclaration)
    def builder(decl):
        params = ', '.join(
            declare(param.type, param.name) for param in decl.params
        )
        if decl.varargs:
            if decl.params:
                varargs = ', ...'
            else:
                varargs = '...'
        else:
            varargs = ''
        return declare(decl.rtype, f'{decl.name}({params}{varargs})')

    @builder.on(types.FunctionType)
    def builder(type, name):
        params = ', '.join(declare(pt, '') for pt in type.ptypes)
        if type.varargs:
            if type.ptypes:
                varargs = ', ...'
            else:
                varargs = '...'
        else:
            varargs = ''
        return declare(type.rtype, f'({name})({params}{varargs})')


@util.multimethod(1)
def gen_header(builder):

    @builder.on(ast.Header)
    def gen(header):
        parts = [f'// {header.mark.source.path}\n']
        for imp in header.imports:
            parts.append(gen_header(imp))
        for decl in header.decls:
            parts.append(gen_header(decl))
        return ''.join(parts)

    @builder.on(ast.AngleBracketImport)
    def gen(imp):
        return f'#include <{imp.path}>\n'

    @builder.on(ast.QuoteImport)
    def gen(imp):
        return f'#include "{imp.path}"\n'

    @builder.on(ast.AbsoluteImport)
    def gen(imp):
        path = imp.path.replace('.', '/')
        return f'#include "{path}"\n'

    @builder.on(ast.FunctionDeclaration)
    def gen(decl):
        return f'{declare(decl)};\n'



@test.case
def sample_test():
    test.equal(
        gen_header(parser.parse_header(r"""
        import <stdio.h>
        int main() {
            printf("Hello world!\n");
            return 0;
        }
        """)),
        r"""// <string>
#include <stdio.h>
int main();
""",
    )

