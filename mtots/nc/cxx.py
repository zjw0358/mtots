"""Dead simple C++ backend
"""
from . import ast
from . import resolver
from mtots import util
import contextlib


class StringBuilder:
    def __init__(self, depth=0):
        self.parts = []
        self.depth = depth

    def __iadd__(self, line):
        self.parts.append(f'{"  " * self.depth}{line}\n')
        return self

    @contextlib.contextmanager
    def indent(self):
        self.depth += 1
        try:
            yield
        finally:
            self.depth -= 1

    def __str__(self):
        return ''.join(self.parts)


_primitive_type_map = {
    'void': 'NCX_VOID',
    'bool': 'NCX_BOOL',
    'int': 'NCX_INT',
    'double': 'NCX_DOUBLE',
    'string': 'NCX_STRING',
}


@util.dataclass
class _Context:
    prologue: StringBuilder
    include: StringBuilder
    fwd: StringBuilder
    hdr: StringBuilder
    src: StringBuilder
    epilogue: StringBuilder

    def _deduped_includes(self):
        lines = []
        seen = set()
        for line in str(self.include).splitlines():
            if line in seen:
                pass
            else:
                lines.append(f'{line}\n')
                seen.add(line)
        return ''.join(lines)

    def __str__(self):
        return ''.join(map(str, [
            self.prologue,
            self._deduped_includes(),
            self.fwd,
            self.hdr,
            self.src,
            self.epilogue,
        ]))


def render(ast_table):
    ctx = _Context(
        prologue=StringBuilder(),
        include=StringBuilder(),
        fwd=StringBuilder(),
        hdr=StringBuilder(),
        src=StringBuilder(),
        epilogue=StringBuilder(),
    )

    for node in ast_table.values():
        _render_file_level_statement(node, ctx)

    return str(ctx)


def _cname(name):
    return 'NCXX_' + (
        name
            .replace('Z', 'ZZ')
            .replace('_', 'ZU')
            .replace('.', 'ZD')
            .replace('$', 'ZR')
            .replace('#', 'ZH')
    )


@util.multimethod(1)
def _render_file_level_statement(on):

    @on(ast.Inline)
    def r(node, ctx):
        if node.type == 'prologue':
            ctx.prologue.parts.append(node.text)
        elif node.type == 'include':
            ctx.include.parts.append(node.text)
        elif node.type == 'fwd':
            ctx.fwd.parts.append(node.text)
        elif node.type == 'hdr':
            ctx.hdr.parts.append(node.text)
        elif node.type == 'src':
            ctx.src.parts.append(node.text)
        elif node.type == 'epilogue':
            ctx.epilogue.parts.append(node.text)
        else:
            raise TypeError(f'Invalid C++ inline type {node.type}')

    @on(ast.Class)
    def r(node, ctx):
        c_class_name = _cname(node.name)

        if node.native:
            ctx.fwd += f'// (native class {node.name}) {c_class_name}'
            for field in node.fields:
                ctx.fwd += f'//   {_declare(field.type, _cname(field.name))}'
            return

        if node.generic:
            tparams = ','.join(
                f'class {_cname(tparam.name)}'
                for tparam in node.type_parameters)
            generic = f'template <{tparams}> '
        else:
            generic = ''

        proto = f'{generic}struct {c_class_name}'

        ctx.fwd += f'{proto};'
        ctx.hdr += f'{proto} ' '{'
        with ctx.hdr.indent():
            for field in node.fields:
                ctx.hdr += f'{_declare(field.type, _cname(field.name))};'
            ctx.hdr += f'virtual ~{c_class_name}()' '{}'
        ctx.hdr += '};'

    @on(ast.Function)
    def r(node, ctx):

        c_function_name = _cname(node.name)
        proto = _declare(node)

        if node.native:
            ctx.fwd += f'// (native function {node.name}) {proto}'
            return

        ctx.hdr += f'{proto};'

        if node.body is not None:
            ctx.src += f'{proto} ' '{'
            with ctx.src.indent():
                ctx.src += f'return {_render_expression(node.body, 1)};'
            ctx.src += '}'


@util.multimethod(1)
def _declare(on):

    @on(ast.Function)
    def r(node):
        if node.generic:
            tparams = ','.join(
                f'class {_cname(tparam.name)}'
                for tparam in node.type_parameters)
            generic = f'template <{tparams}> '
        else:
            generic = ''
        c_function_name = _cname(node.name)
        parameters = ', '.join(_declare(param) for param in node.parameters)
        dtor = f'{c_function_name}({parameters})'
        return f'{generic}{_declare(node.return_type, dtor)}'

    @on(ast.Parameter)
    def r(node):
        return f'{_declare(node.type, _cname(node.name))}'

    @on(ast.TypeParameter)
    def r(type_, dtor):
        return f'{_cname(type_.name)} {dtor}'

    @on(ast.PrimitiveType)
    def r(type_, dtor):
        return f'{_primitive_type_map[type_.name]} {dtor}'

    @on(ast.Class)
    def r(type_, dtor):
        return f'NCX_PTR<{_cname(type_.name)}> {dtor}'

    @on(ast.ReifiedType)
    def r(type_, dtor):
        class_ = type_.class_
        args = ','.join(
            _declare(arg, '').strip() for arg in type_.type_arguments)
        return f'NCX_PTR<{_cname(class_.name)}<{args}>> {dtor}'


@util.multimethod(1)
def _render_expression(on):
    @on(ast.Block)
    def r(node, depth):
        parts = []
        parts.append('([&](){\n')
        exprs = node.expressions
        inner_indent = '  ' * (depth + 1)
        if exprs:
            for expr in exprs[:-1]:
                parts.append(
                    f'{inner_indent}'
                    f'{_render_expression(expr, depth + 1)};\n')
            parts.append(
                f'{inner_indent}'
                f'return {_render_expression(exprs[-1], depth + 1)};\n'
            )
        else:
            parts.append(f'{inner_indent}return 0;\n')
        parts.append('  ' * depth + '})()')
        return ''.join(parts)

    @on(ast.LocalVariableDeclaration)
    def r(node, depth):
        cname = _cname(node.name)
        expr = _render_expression(node.expression, depth)
        return f'{_declare(node.type, cname)} = {expr}'

    @on(ast.FunctionCall)
    def r(node, depth):
        c_function_name = _cname(node.function.name)
        arguments = ', '.join(
            _render_expression(e, depth) for e in node.arguments)
        return f'{c_function_name}({arguments})'

    @on(ast.Int)
    def r(node, depth):
        return f'{node.value}L'

    @on(ast.String)
    def r(node, depth):
        contents = (
            node.value
                .replace('\n', '\\n')
                .replace('\\', '\\\\')
        )
        return f'NCX_mkstr("{contents}")'

    @on(ast.LocalVariable)
    def r(node, depth):
        return _cname(node.declaration.name)


def main():
    data = resolver.load(r"""
    void main() = {
        print("Hello world!")
    }
    """)
    print(render(data))


if __name__ == '__main__':
    main()
