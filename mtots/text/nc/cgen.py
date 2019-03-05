"""C Code Generator

For now, generates a single C code blob
"""
from . import ast
from . import loader
from . import resolver
from . import types
from mtots import util
from mtots.util import dataclasses
import contextlib
import json
import re

NORMAL_NAME_PATTERN = re.compile(r'[a-zA-Z0-9_]+')
SPECIAL_NAME_PATTERN = re.compile(r'@[a-zA-Z0-9_$]+')


def gen(node: ast.TranslationUnit):
    ctx = _Context()
    _gen(node, ctx)
    return str(ctx)


@util.dataclass
class _Context:
    fwd: list = dataclasses.field(default_factory=lambda: [])
    hdr: list = dataclasses.field(default_factory=lambda: [])
    src: list = dataclasses.field(default_factory=lambda: [])
    tu_set: set = dataclasses.field(default_factory=lambda: set())
    depth: int = 0

    def indent(self):
        self.src.append(self.depth * '  ')

    @contextlib.contextmanager
    def push_indent(self):
        self.depth += 1
        try:
            yield
        finally:
            self.depth -= 1

    def __iadd__(self, line):
        self.indent()
        self.src.append(line)
        self.src.append('\n')

    def __str__(self):
        return ''.join(''.join(map(str, xs))
                       for xs in [self.fwd, self.hdr, self.src])


@util.multimethod(1)
def _gen(on):

    @on(ast.TranslationUnit)
    def r(node, ctx):
        key = id(node)
        if key not in ctx.tu_set:
            for stmt in node.stmts:
                _gen(stmt, ctx)
            ctx.tu_set.add(key)

    @on(ast.Import)
    def r(node, ctx):
        _gen(node.tu, ctx)

    @on(ast.InlineBlob)
    def r(node, ctx):
        if node.type == 'fwd':
            ctx.fwd.append(node.text)
        elif node.type == 'hdr':
            ctx.hdr.append(node.text)
        elif node.type == 'src':
            ctx.src.append(node.text)
        else:
            raise TypeError(f'Invalid blob type {node.type}')

    @on(ast.NativeTypedef)
    def r(node, ctx):
        pass

    @on(ast.FunctionDefinition)
    def r(node, ctx):
        if not node.native:
            proto = _declare(node.proto)
            ctx.hdr.append(f'{proto};\n')
            ctx.src.append(f'{proto} ')
            _gen(node.body, ctx, first_indent=False)

    @on(ast.Block)
    def r(node, ctx, first_indent=True):
        if first_indent:
            ctx.indent()
        ctx.src.append('{\n')
        with ctx.push_indent():
            for stmt in node.stmts:
                _gen(stmt, ctx)
        ctx += '}'

    @on(ast.ExpressionStatement)
    def r(node, ctx):
        ctx += f'{_gen(node.expr)};'

    @on(ast.Return)
    def r(node, ctx):
        ctx += f'return {_gen(node.expr)};'

    @on(ast.FunctionCall)
    def r(node):
        f = _gen(node.f)
        args = ', '.join(map(_gen, node.args))
        return f'({f})({args})'

    @on(ast.FunctionName)
    def r(node):
        return _n(node.name)

    @on(ast.IntLiteral)
    def r(node):
        return str(node.value)

    @on(ast.StringLiteral)
    def r(node):
        # TODO: Do this more cleanly
        return f'"{json.dumps(node.value)[1:-1]}"'


def _n(name):
    if NORMAL_NAME_PATTERN.match(name):
        return name
    elif SPECIAL_NAME_PATTERN.match(name):
        new_name = (
            'NCX_' +
            name[1:]
                .replace('Z', 'ZZ')
                .replace('$', 'ZD')
                .replace('_', 'ZU')
        )
        assert NORMAL_NAME_PATTERN.match(new_name), (name, new_name)
        return new_name
    else:
        raise TypeError(f'Invalid identifier {repr(name)}')


@util.multimethod(1)
def _declare(on):

    @on(ast.FunctionPrototype)
    def r(proto):
        name = _n(proto.name)
        params = ', '.join(_declare(p) for p in proto.params)
        varargs = ', ...' if proto.varargs else ''
        return _declare(proto.rtype, f'{name}({params}{varargs})')

    @on(ast.Parameter)
    def r(node):
        return _declare(node.type, _n(node.name))

    @on(types.PointerType)
    def r(node, declarator):
        return _declare(node.type, f'*{declarator}')

    @on(types.ConstType)
    def r(node, declarator):
        return _declare(node.type, f'const {declarator}')

    @on(types._PrimitiveType)
    def r(node, declarator):
        return f'{node.name} {declarator}'


print(gen(resolver.resolve(loader.load(r"""
import stdio

int main() {
    printf("Hello world!\n");
    return 0;
}
"""))))
