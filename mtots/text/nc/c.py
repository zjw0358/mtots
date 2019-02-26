"""C codegen
"""
from . import ast
from . import parser
from . import types
from mtots import test
from mtots import util


def guard_from_import_path(import_path):
    return import_path.replace('.', '_').upper() + '_NC'


def forward_path_from_import_path(import_path):
    return import_path + '.nc.fwd.h'


def header_path_from_import_path(import_path):
    return import_path + '.nc.h'


def source_path_from_import_path(import_path):
    return import_path + '.nc.c'


def _n(name):
    """Convert to C name.
    Most names translate to just themselves, except for
    names with '$' in them.
    """
    return name.replace('$', 'NCIDXXX')


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
        return declare(decl.rtype, f'{_n(decl.name)}({params}{varargs})')

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
def gen_forward(builder):

    @builder.on(ast.Header)
    def gen(header, *, includes=True):
        guard = guard_from_import_path(header.import_path) + '_FWDH'
        parts = []
        if includes:
            parts.extend([
                f'#ifndef {guard}\n',
                f'#define {guard}\n',
                f'/* (NC FORWARD HEADER) {header.import_path} */\n',
            ])
        if includes:
            parts.append(f'#endif/*{guard}*/\n')
        return ''.join(parts)


@util.multimethod(1)
def gen_header(builder):

    @builder.on(ast.Header)
    def gen(header, *, includes=True):
        guard = guard_from_import_path(header.import_path) + '_H'
        forward_path = forward_path_from_import_path(header.import_path)
        parts = []
        if includes:
            parts.extend([
                f'#ifndef {guard}\n',
                f'#define {guard}\n',
                f'/* (NC HEADER) {header.import_path} */\n',
                f'#include "{forward_path}"\n',
            ])
            for imp in header.imports:
                parts.append(gen_header(imp))
        for decl in header.decls:
            parts.append(gen_header(decl))
        if includes:
            parts.append(f'#endif/*{guard}*/\n')
        return ''.join(parts)

    @builder.on(ast.AngleBracketImport)
    def gen(imp):
        return f'#include <{imp.path}>\n'

    @builder.on(ast.QuoteImport)
    def gen(imp):
        return f'#include "{imp.path}"\n'

    @builder.on(ast.AbsoluteImport)
    def gen(imp):
        forward_path = forward_path_from_import_path(imp.path)
        return f'#include "{forward_path}"\n'

    @builder.on(ast.FunctionDeclaration)
    def gen(decl):
        return f'{declare(decl)};\n'


@util.multimethod(1)
def gen_source(builder):

    def _make_indent(depth):
        return '  ' * depth

    def _add_lineno(node, buf, debug_info):
        if debug_info:
            buf.append(f'#line {node.mark.lineno}\n')

    @builder.on(ast.Source)
    def gen(source, *, includes=True, debug_info=True):
        import_path = source.import_path
        header_path = header_path_from_import_path(import_path)
        file_path = source.mark.source.path
        assert '"' not in file_path, file_path
        parts = []

        if includes:
            parts.extend([
                f'/* (NC SOURCE) {import_path} */\n',
                f'#include "{header_path}"\n',
            ])

        if debug_info:
            parts.append(f'#line 1 "{file_path}"\n')

        if includes:
            for imp in source.imports:
                parts.append(gen_source(imp))

        for decl in source.decls:
            if isinstance(decl, ast.Definition):
                _add_lineno(decl, parts, debug_info)
                parts.append(gen_source(decl, debug_info=debug_info))
        return ''.join(parts)

    @builder.on(ast.AngleBracketImport)
    def gen(imp):
        return ''  # already included in header

    @builder.on(ast.QuoteImport)
    def gen(imp):
        return ''  # already included in header

    @builder.on(ast.AbsoluteImport)
    def gen(imp):
        header_path = header_path_from_import_path(imp.path)
        return f'#include "{header_path}"\n'

    @builder.on(ast.FunctionDefinition)
    def gen(defn, *, debug_info):
        buffer = []
        buffer.extend([
            declare(defn), ' ',
        ])
        gen_source(
            defn.body,
            buffer,
            0,
            first_indent=False,
            debug_info=debug_info,
        )
        return ''.join(buffer)

    @builder.on(ast.Block)
    def gen(block, buf, depth, *, debug_info, first_indent=True):
        indent = _make_indent(depth)
        if first_indent:
            buf.append(indent)
        buf.append('{\n')
        for stmt in block.stmts:
            _add_lineno(stmt, buf, debug_info=debug_info)
            gen_source(stmt, buf, depth + 1, debug_info=debug_info)
        buf.append(indent + '}\n')

    @builder.on(ast.ExpressionStatement)
    def gen(ret, buf, depth, *, debug_info):
        buf.append(_make_indent(depth))
        buf.append(gen_source(ret.expr))
        buf.append(';\n')

    @builder.on(ast.Return)
    def gen(ret, buf, depth, *, debug_info):
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
        return f'{_n(node.name)}({args})'

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
        r"""#ifndef __MAIN___NC_H
#define __MAIN___NC_H
/* (NC HEADER) __main__ */
#include "__main__.nc.fwd.h"
#include <stdio.h>
int main();
#endif/*__MAIN___NC_H*/
""",
    )

