"""C codegen
"""
from . import ast
from . import parser
from . import types
from mtots import test
from mtots import util


def header_path_from_import_path(import_path):
    return import_path + '.nc.h'


def source_path_from_import_path(import_path):
    return import_path + '.nc.c'


@util.multimethod(1)
def declare(builder):

    @builder.on(types._PrimitiveType)
    def builder(type, name):
        return f'{type.name} {name}'

    @builder.on(types.NamedType)
    def builder(type, name):
        return f'{type.name} {name}'

    @builder.on(types.PointerType)
    def builder(type, name):
        return declare(type.type, f'*{name}')

    @builder.on(types.ConstType)
    def builder(type, name):
        return declare(type.type, f'const {name}')

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
        parts = [f'// (NC HEADER) {header.import_path}\n']
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
        header_path = header_path_from_import_path(imp.path)
        return f'#include "{header_path}"\n'

    @builder.on(ast.FunctionDeclaration)
    def gen(decl):
        return f'{declare(decl)};\n'


@util.multimethod(1)
def gen_source(builder):

    def _make_indent(depth):
        return '  ' * depth

    @builder.on(ast.Source)
    def gen(source):
        import_path = source.import_path
        header_path = header_path_from_import_path(import_path)
        parts = [
            f'// (NC SOURCE) {import_path}\n',
            f'#include "{header_path}"\n',
        ]
        for decl in source.decls:
            if isinstance(decl, ast.Definition):
                parts.append(gen_source(decl))
        return ''.join(parts)

    @builder.on(ast.FunctionDefinition)
    def gen(defn):
        buffer = [
            declare(defn), ' ',
        ]
        gen_source(defn.body, buffer, 0, first_indent=False)
        return ''.join(buffer)

    @builder.on(ast.Block)
    def gen(block, buf, depth, first_indent=True):
        indent = _make_indent(depth)
        if first_indent:
            buf.append(indent)
        buf.append('{\n')
        for stmt in block.stmts:
            gen_source(stmt, buf, depth + 1)
        buf.append(indent + '}\n')

    @builder.on(ast.ExpressionStatement)
    def gen(ret, buf, depth):
        buf.append(_make_indent(depth))
        buf.append(gen_source(ret.expr))
        buf.append(';\n')

    @builder.on(ast.Return)
    def gen(ret, buf, depth):
        buf.append(_make_indent(depth))
        if ret.expr:
            buf.append(f'return {gen_source(ret.expr)};\n')
        else:
            buf.append('return;\n')

    @builder.on(ast.IntLiteral)
    def gen(node):
        return str(node.value)

    @builder.on(ast.FunctionCall)
    def gen(node):
        args = ', '.join(map(gen_source, node.args))
        return f'{node.name}({args})'

    _ESCAPE_MAP = {
        '\b': 'b',
        '\t': 't',
        '\n': 'n',
        '\f': 'f',
        '\r': 'r',
        '\"': '\"',
        '\'': '\'',
        '\\': '\\',
    }

    @builder.on(ast.StringLiteral)
    def gen(node):
        parts = []
        for c in node.value:
            if c in _ESCAPE_MAP:
                parts.append('\\' + _ESCAPE_MAP[c])
            elif 32 <= ord(c) < 127:
                parts.append(c)
            else:
                # TODO: Support unicode characters
                parts.append('\\%03o' % ord(c))
        return '"' + ''.join(parts) + '"'


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

