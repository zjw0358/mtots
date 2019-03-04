from . import ast
from . import cst
from . import errors
from . import loader
from . import types
from mtots import util
import contextlib
import typing


class Scope:
    def __init__(self, parent):
        self.parent = parent
        self.table = {}

    def get(self, key, stack):
        if key in self.table:
            return self.table[key]
        elif self.parent:
            return self.parent.get(key, stack)
        else:
            raise errors.TypeError(stack, f'Symbol {repr(key)} not found')

    def set(self, key, value, stack):
        if key in self.table:
            raise errors.TypeError(
                stack, f'Duplicate definition for {repr(key)}')
        self.table[key] = value

    def __contains__(self, key):
        return key in self.table or self.parent and key in self.parent

    def __getitem__(self, key):
        if key in self.table or self.parent is None:
            return self.table[key]
        else:
            return self.parent[key]

    def __setitem__(self, key, value):
        self.table[key] = value


class Stack:
    def __init__(self):
        self.marks = []

    def __iter__(self):
        return iter(self.marks)

    @contextlib.contextmanager
    def push_mark(self, *marks):
        self.marks.extend(marks)
        try:
            yield
        finally:
            del self.marks[-len(marks):]


@util.dataclass(frozen=True)
class Context:
    stack: Stack
    scope: Scope
    type_map: typing.Dict[str, str]
    cst_map: typing.Dict[str, cst.TranslationUnit]
    tu_cache: typing.Dict[str, ast.TranslationUnit]

    @contextlib.contextmanager
    def push_scope(self):
        yield Context(
            stack=self.stack,
            scope=Scope(self.scope),
            type_map=self.type_map,
            cst_map=self.cst_map,
            tu_cache=self.tu_cache,
        )

    def push_mark(self, *marks):
        return self.stack.push_mark(*marks)

    def __getitem__(self, key):
        return self.scope.get(key, self.stack)

    def __setitem__(self, key, value):
        self.scope.set(key, value, self.stack)

    def resolve_import(self, import_path):
        if import_path not in self.tu_cache:
            self.tu_cache[import_path] = _resolve(
                self.cst_map[import_path],
                self,
            )
        return self.tu_cache[import_path]

    def error(self, message):
        return errors.TypeError(self.stack, message)


def _make_type_map(cst_map):
    type_map = {}
    for tu in cst_map.values():
        for stmt in tu.stmts:
            if isinstance(stmt, cst.NativeTypedef):
                type_map[stmt.name] = 'TYPEDEF'
            elif isinstance(stmt, cst.StructDefinition):
                if stmt.typedef:
                    type_map[stmt.name] = 'TYPEDEF'
                else:
                    type_map[stmt.name] = 'STRUCT'
    return type_map


def resolve(cst_map):
    ctx = Context(
        stack=Stack(),
        scope=Scope(None),
        type_map=_make_type_map(cst_map=cst_map),
        cst_map=cst_map,
        tu_cache=dict(),
    )
    return ctx.resolve_import('MAIN')


@util.multimethod(1)
def _resolve(on):
    @on(cst.TranslationUnit)
    def r(cst_tu, ctx):
        stmt_thunks = [_resolve(stmt, ctx) for stmt in cst_tu.stmts]
        return ast.TranslationUnit(
            mark=cst_tu.mark,
            stmts=tuple(thunk() for thunk in stmt_thunks),
        )

    @on(cst.PrimitiveType)
    def r(cst_node, ctx):
        return cst_node.type

    @on(cst.PointerType)
    def r(cst_node, ctx):
        return types.PointerType(_resolve(cst_node.type, ctx))

    @on(cst.ConstType)
    def r(cst_node, ctx):
        return types.ConstType(_resolve(cst_node.type, ctx))

    @on(cst.InlineBlob)
    def r(cst_blob, ctx):
        return lambda: ast.InlineBlob(
            mark=cst_blob.mark,
            type=cst_blob.type,
            text=cst_blob.text,
        )

    @on(cst.Import)
    def r(cst_import, ctx):
        tu = ctx.resolve_import(cst_import.path)
        return lambda: ast.Import(
            mark=cst_import.mark,
            path=cst_import.path,
            tu=tu,
        )

    @on(cst.NativeTypedef)
    def r(cst_typedef, ctx):
        return lambda: ast.NativeTypedef(
            mark=cst_typedef.mark,
            name=cst_typedef.name,
        )

    @on(cst.Parameter)
    def r(cst_node, ctx):
        return ast.Parameter(
            mark=cst_node.mark,
            type=_resolve(cst_node.type, ctx),
            name=cst_node.name,
        )

    @on(cst.FunctionDefinition)
    def r(cst_fd, ctx):
        proto = ast.FunctionPrototype(
            mark=cst_fd.mark,
            native=cst_fd.native,
            rtype=_resolve(cst_fd.rtype, ctx),
            name=cst_fd.name,
            params=tuple(_resolve(p, ctx) for p in cst_fd.params),
            varargs=cst_fd.varargs,
        )
        ctx[proto.name] = proto
        with ctx.push_scope() as ictx:
            for param in proto.params:
                ictx[param.name] = param
            body_thunk = lambda: (
                None if cst_fd.body is None else _resolve(cst_fd.body, ictx)
            )
        return lambda: ast.FunctionDefinition(
            mark=cst_fd.mark,
            proto=proto,
            body=body_thunk(),
        )

    @on(cst.Block)
    def r(cst_block, ctx):
        return ast.Block(
            mark=cst_block.mark,
            stmts=tuple(_resolve(stmt, ctx) for stmt in cst_block.stmts),
        )

    @on(cst.ExpressionStatement)
    def r(cst_stmt, ctx):
        return ast.ExpressionStatement(
            mark=cst_stmt.mark,
            expr=_resolve(cst_stmt.expr, ctx),
        )

    @on(cst.Return)
    def r(cst_stmt, ctx):
        return ast.Return(
            mark=cst_stmt.mark,
            expr=_resolve(cst_stmt.expr, ctx),
        )

    @on(cst.IntLiteral)
    def r(cst_node, ctx):
        return ast.IntLiteral(
            mark=cst_node.mark,
            type=types.INT,
            value=cst_node.value,
        )

    @on(cst.StringLiteral)
    def r(cst_node, ctx):
        return ast.StringLiteral(
            mark=cst_node.mark,
            type=types.PointerType(types.ConstType(types.CHAR)),
            value=cst_node.value,
        )

    @on(cst.Variable)
    def r(cst_node, ctx):
        name = cst_node.name
        with ctx.push_mark(cst_node.mark):
            decl = ctx[name]
        if isinstance(decl, ast.FunctionPrototype):
            return ast.FunctionName(
                mark=cst_node.mark,
                type=decl.type,
                proto=decl,
            )
        elif isinstance(decl, ast.Parameter):
            return ast.LocalVariable(
                mark=cst_node.mark,
                type=decl.type,
                decl=decl,
            )
        with ctx.push_mark(cst_node.mark):
            raise ctx.error(f'{repr(name)} is not a variable')

    @on(cst.FunctionCall)
    def r(cst_node, ctx):
        f = _resolve(cst_node.f, ctx)
        args = tuple(_resolve(arg, ctx) for arg in cst_node.args)
        if isinstance(f.type, types.PointerType):
            ftype = f.type.type
        else:
            ftype = f.type
        if not isinstance(ftype, types.FunctionType):
            with ctx.push_mark(cst_node.mark):
                raise ctx.error('Not a function')
        argtypes = [arg.type for arg in args]
        if not ftype.can_apply_to_argtypes(argtypes):
            with ctx.push_mark(cst_node.mark):
                raise ctx.error(
                    'Function cannot be applied to given args: '
                    f'{ftype} vs {argtypes}'
                )
        return ast.FunctionCall(
            mark=cst_node.mark,
            type=ftype.rtype,
            f=f,
            args=args,
        )


print(resolve(loader.load(r"""
import stdio

int main() {
    printf("Hello world!\n");
    return 0;
}
""")))

