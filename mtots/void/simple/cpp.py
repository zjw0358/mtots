"""Simple C++ backend
Creates a single C++ file
"""
from . import ast
from . import parser
from . import types
from mtots import util
from mtots.parser import base
import contextlib


def _flatten(module_table):
    global_dict = {}
    for module in module_table.values():
        for node in module.vars + module.funcs + module.clss:
            if '_' in node.name:
                raise base.Error(
                    [node.mark],
                    'Global names with underscores are not yet supported')
            global_dict[node.name] = node
    return global_dict


def _sanitize(name, prefix='NCX'):
    return prefix + (
        name
            .replace('Z', 'ZZ')
            .replace('.', 'ZD')
            .replace('_', 'ZU')
            .replace('#', 'ZH')
    )


OBJECT = _sanitize(ast.OBJECT)
STRING = _sanitize(ast.STRING)


_HDR_PRELUDE = fr"""
#include <iostream>
#include <memory>
#include <stdio.h>
#include <string>
struct {OBJECT} {{
    long refcnt;
    {OBJECT}::{OBJECT}(): refcnt(0) {{}}
}};
struct {STRING} : {OBJECT} {{
    const std::string data;
    {STRING}::{STRING}(const std::string &d): data(d) {{}}
}};
"""


def render(module_table):
    global_dict = _flatten(module_table)

    indent_depth = 0

    @contextlib.contextmanager
    def push_indent():
        nonlocal indent_depth
        indent_depth += 1
        try:
            yield
        finally:
            indent_depth -= 1

    def indent():
        src.append('  ' * indent_depth)

    def class_depth(node):
        if node.base is None:
            return 0
        else:
            return 1 + class_depth(get_base_class(node))

    def get_base_class(node):
        if node.base is None:
            return None
        else:
            base_class = global_dict[node.base]
            assert isinstance(base_class, ast.Class), (
                node,
                node.base,
                base_class,
            )
            return base_class

    def node_key(node):
        if isinstance(node, ast.Class):
            type_priority = 0
            depth = class_depth(node)
        elif isinstance(node, ast.Function):
            type_priority = 1
            depth = 0
        elif isinstance(node, ast.GlobalVariable):
            type_priority = 2
            depth = 0
        else:
            raise TypeError(node)

        return type_priority, depth, node.name

    global_nodes = sorted(global_dict.values(), key=node_key)

    fwd = []
    hdr = []
    src = []

    @util.multimethod(1)
    def declare(on):

        @on(types.ClassType)
        def d(self, name):
            return f'std::shared_ptr<{cname(self)}> {name}'.strip()

        @on(types._PrimitiveType)
        def d(self, name):
            return f'{cname(self)} {name}'.strip()

        @on(ast.Function)
        def d(self):
            name = cname(self)
            params = ', '.join(declare(param) for param in self.params)
            decl = f'{name}({params})'
            return declare(self.rtype, decl).strip()

        @on(ast.Method)
        def d(self, inside_class):
            name = cname(self, inside_class=inside_class)
            params = ', '.join(declare(param) for param in self.params)
            decl = f'{name}({params})'
            return declare(self.rtype, decl).strip()

        @on(ast.Parameter)
        def d(self):
            return declare(self.type, _sanitize(self.name)).strip()

    @util.multimethod(1)
    def cname(on):
        @on(types.ClassType)
        def n(self):
            return _sanitize(self.name)

        @on(types._PrimitiveType)
        def n(self):
            if self is types.VOID:
                return 'int'
            elif self is types.INT:
                return 'long'
            elif self is types.DOUBLE:
                return 'dobule'
            else:
                raise TypeError(self)

        @on(ast.Method)
        def n(self, inside_class=False):
            class_name, short_name = self.name.split('#')
            c_short_name = _sanitize(short_name)
            c_class_name = _sanitize(class_name)
            return (
                f'{c_class_name}::{c_short_name}'
                if inside_class else
                c_short_name
            )

        @on(ast.Function)
        def n(self):
            return _sanitize(self.name)

        @on(ast.Class)
        def n(self):
            return _sanitize(self.name)

    def writeln(line):
        indent()
        src.append(line)
        src.append('\n')

    @util.multimethod(1)
    def render(on):

        @on(ast.Class)
        def r(self):
            if self.native:
                return
            name = cname(self)
            superclass_name = cname(get_base_class(self))
            fwd.append(f'typedef struct {name} {name};\n')

            hdr.append(f'struct {name} : {superclass_name} ' '{\n')
            for field in self.fields:
                ftype = field.type
                fname = _sanitize(field.name)
                hdr.append(f'  {declare(ftype, fname)};\n')
            for method in self.methods:
                hdr.append(f'  {declare(method, inside_class=True)};\n')
            hdr.append('};\n')

            for method in self.methods:
                src.append(f'{declare(method, inside_class=False)} ')
                render(method.body, first_indent=False)

        @on(ast.Function)
        def r(self):
            if self.native:
                return
            hdr.append(f'{declare(self)};\n')
            src.append(f'{declare(self)} ')
            render(self.body, first_indent=False)

        @on(ast.GlobalVariable)
        def r(self):
            pass

        @on(ast.Block)
        def r(self, first_indent=True):
            if first_indent:
                indent()
            src.append('{\n')
            with push_indent():
                for stmt in self.stmts:
                    render(stmt)
            writeln('}')

        @on(ast.ExpressionStatement)
        def r(self):
            writeln(f'{render(self.expr)};')

        @on(ast.Return)
        def r(self):
            if self.expr is None:
                writeln('return 0;')
            else:
                writeln(f'return {render(self.expr)};')

        @on(ast.IntLiteral)
        def r(self):
            return str(self.value)

        @on(ast.StringLiteral)
        def r(self):
            return f'std::make_shared<{STRING}>("{self.value}")'

        @on(ast.FunctionCall)
        def r(self):
            name = cname(self.f)
            args = ', '.join(map(render, self.args))
            return f'{name}({args})'

    for node in global_nodes:
        render(node)

    return _HDR_PRELUDE + ''.join(map(''.join, [fwd, hdr, src]))




# print(render(parser.parse("""
#
# int x = 10;
#
# int main() {
#     print("Hello world!");
#     return 0;
# }
#
# class Foo {
#     int foo() {
#         return 0;
#     }
# }
#
# """)))


