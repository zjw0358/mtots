"""Resolve AST statement and expression nodes with
type information not immediately available at parse time.

In particular, resolving a node should make sure that
    Expression nodes have their 'type' field set, and
    Stataement nodes have their 'rstates' field set.
"""
from . import ast
from . import errors
from . import types
from .rstates import NoReturn
from .rstates import Returns
from .rstates import ReturnState
from .scopes import Scope
from mtots import util


def resolve(node, scope):
    new_node = _resolve(node, scope)

    assert isinstance(new_node, ast.StatementOrExpression), new_node
    if isinstance(new_node, ast.Statement):
        assert isinstance(new_node.rstates, set), new_node.rstates
        assert all(
            isinstance(state, ReturnState)
            for state in new_node.rstates
        ), new_node.rstates
    elif isinstance(new_node, ast.Expression):
        assert isinstance(new_node.type, types.Type), new_node.type

    return new_node


@util.multimethod(1)
def _resolve(b):

    @b.on(ast.ExpressionStatement)
    def r(stmt, scope):
        return ast.ExpressionStatement(
            mark=stmt.mark,
            expr=resolve(stmt.expr, scope),
            rstates={NoReturn()},
        )

    @b.on(ast.If)
    def r(self, scope):
        cond = resolve(self.cond, scope)
        body = resolve(self.body, scope)
        other = resolve(self.other, scope) if self.other else None
        return ast.If(
            mark=self.mark,
            cond=cond,
            body=body,
            other=other,
            rstates=(
                body.rstates |
                (other.rstates if other else {NoReturn()})
            ),
        )

    @b.on(ast.While)
    def r(self, scope):
        cond = resolve(self.cond, scope)
        body = resolve(self.body, scope)
        return ast.While(
            mark=self.mark,
            cond=cond,
            body=body,
            rstates={NoReturn()} | body.rstates,
        )

    @b.on(ast.Return)
    def r(self, scope):
        expr = resolve(self.expr, scope)
        return ast.Return(
            mark=self.mark,
            expr=expr,
            rstates={Returns(expr.type)},
        )

    @b.on(ast.Block)
    def r(self, scope):
        inner_scope = Scope(scope)
        stmts = list(resolve(stmt, inner_scope) for stmt in self.stmts)

        nr = NoReturn()
        rstates = {nr}
        for i, stmt in enumerate(stmts):
            if i and nr not in stmts[i - 1].rstates:
                raise errors.TypeError([stmt.mark], 'Unrechable statement')
            rstates |= stmt.rstates
        if stmts and nr not in stmts[-1].rstates:
            rstates.discard(nr)

        return ast.Block(
            mark=self.mark,
            stmts=stmts,
            rstates=rstates,
        )

    @b.on(ast.IntLiteral)
    def r(self, scope):
        return self

    @b.on(ast.StringLiteral)
    def r(self, scope):
        return self

    @b.on(ast.FunctionCall)
    def r(self, scope):
        decl = scope.get(self.name, [self.mark])
        if not isinstance(decl, ast.FunctionDeclaration):
            raise errors.TypeError(
                [self.mark, decl.mark],
                f'{self.name} is not a function',
            )
        args = [resolve(arg, scope) for arg in self.args]
        _check_func_call_params(self, args, decl)
        return ast.FunctionCall(
            mark=self.mark,
            name=self.name,
            args=args,
            decl=decl,
            type=decl.rtype,
        )

    def _check_func_call_params(self, args, decl):
        if decl.varargs:
            if len(decl.params) < len(args):
                raise errors.TypeError(
                    [self.mark, decl.mark],
                    f'Expected at least {len(decl.params)} args '
                    f'but got {len(args)} args.'
                )
        else:
            if len(decl.params) != len(args):
                raise errors.TypeError(
                    [self.mark, decl.mark],
                    f'Expected {len(decl.params)} args '
                    f'but got {len(args)} args.'
                )
        for param, arg in zip(decl.params, args):
            if not types.convertible(arg.type, param.type):
                raise errors.TypeError(
                    [arg.mark, param.mark],
                    f'Expected type {param.type} but got {arg.type}',
                )

