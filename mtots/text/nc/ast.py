from . import errors
from . import types
from .rstates import NoReturn
from .rstates import Returns
from .rstates import ReturnState
from .scopes import Scope
from .types import Type
from mtots import util
from mtots.text import base
import abc
import typing

Node = base.Node


@util.dataclass
class BaseImport(Node):
    path: str


@util.dataclass
class CeeImport(BaseImport):
    pass


@util.dataclass
class AngleBracketImport(CeeImport):
    pass


@util.dataclass
class QuoteImport(CeeImport):
    pass


@util.dataclass
class AbsoluteImport(BaseImport):
    pass


@util.dataclass
class Declaration(Node):
    name: str


class VariableDeclaration(Declaration):
    # NOTE: abstract field 'type: Type'
    pass


class GlobalDeclaration(Declaration):
    pass


@util.dataclass
class Header(Node):
    "All the information needed to generate a C header"
    imports: typing.List[BaseImport]
    decls: typing.List[GlobalDeclaration]

    @property
    def import_path(self):
        return self.mark.source.metadata['import_path']


@util.dataclass
class Source(Node):
    "Like Header, but FunctionDefinitions are properly parsed"
    imports: typing.List[BaseImport]
    decls: typing.List[GlobalDeclaration]

    @property
    def import_path(self):
        return self.mark.source.metadata['import_path']


class Definition(Declaration):
    pass


@util.dataclass
class Field(Node):
    type: Type
    name: str


@util.dataclass
class StructDeclaration(GlobalDeclaration):
    pass


@util.dataclass
class StructDefinition(StructDeclaration, Definition):
    native: bool  # indicates if this struct is already defined in C code
    fields: typing.List[Field]


@util.dataclass
class Param(VariableDeclaration, Definition):
    type: Type
    name: str


@util.dataclass
class FunctionDeclaration(GlobalDeclaration):
    rtype: Type
    attrs: typing.List[str]
    params: typing.List['Param']
    varargs: bool


@util.dataclass
class FunctionDefinition(FunctionDeclaration, Definition):
    body: 'Block'


class StatementOrExpression(Node, metaclass=abc.ABCMeta):

    @classmethod
    def _recursively_annotate(cls, node, scope):
        if isinstance(node, Node):
            if isinstance(node, Block):
                inner_scope = Scope(scope)
            else:
                inner_scope = scope

            for field_name in type(node).__dataclass_fields__:
                field = getattr(node, field_name)
                cls._recursively_annotate(field, inner_scope)

            if isinstance(node, (Statement, Expression)):
                node._annotate(inner_scope)

        elif isinstance(node, (list, tuple, set, frozenset)):
            for child in node:
                cls._recursively_annotate(child, scope)

        elif isinstance(node, dict):
            for key, value in node.items():
                cls._recursively_annotate(key, scope)
                cls._recursively_annotate(value, scope)

        elif node is None or isinstance(node, (bool, int, float, str, Type)):
            # If we see a scalar, nothing to do
            pass

        else:
            raise TypeError(node)

    def annotate(self, scope):
        StatementOrExpression._recursively_annotate(self, scope)


class Statement(StatementOrExpression):
    _rstates = None  # return states (Set[ReturnState])

    def _annotate(self, scope):
        if self._rstates is None:
            self._rstates = frozenset(self._get_return_states(scope))

    @abc.abstractmethod
    def _get_return_states(self, scope):
        pass

    @property
    def rstates(self):
        if self._rstates is None:
            raise TypeError(f'.rstates accessed before annotate called')
        return self._rstates


class Expression(StatementOrExpression):
    _type = None

    def _annotate(self, scope):
        if self._type is None:
            self._type = self._get_type(scope)

    @property
    def type(self):
        if self._type is None:
            raise TypeError(f'.type accessed before annotate called')
        return self._type

    @abc.abstractmethod
    def _get_type(self, scope):
        pass


@util.dataclass
class ExpressionStatement(Statement):
    expr: Expression

    def _get_return_states(self, scope):
        return {NoReturn()}


@util.dataclass
class If(Statement):
    cond: Expression
    body: Statement
    other: typing.Optional[Statement]

    def _get_return_states(self, scope):
        return (
            self.body.rstates |
            (self.other.rstates if self.other else {NoReturn()})
        )


@util.dataclass
class While(Statement):
    cond: Expression
    body: Statement

    def _get_return_states(self, scope):
        return {NoReturn()} | self.body.rstates


@util.dataclass
class Return(Statement):
    expr: typing.Optional[Expression]

    def _get_return_states(self, scope):
        return {Returns(self.expr.type)}


@util.dataclass
class Block(Statement):
    stmts: typing.List[Statement]

    def _get_return_states(self, scope):
        for stmt in self.stmts:
            stmt.annotate(scope)

        nr = NoReturn()
        stmts = self.stmts
        rstates = {nr}
        for i, stmt in enumerate(stmts):
            if i and nr not in stmts[i - 1].rstates:
                raise errors.TypeError([stmt.mark], f'Unrechable statement')
            rstates |= stmt.rstates
        if stmts and nr not in stmts[len(stmts) - 1].rstates:
            rstates.discard(nr)
        return rstates


@util.dataclass
class IntLiteral(Expression):
    value: int

    def _get_type(self, scope):
        return types.INT


@util.dataclass
class StringLiteral(Expression):
    value: str

    def _get_type(self, scope):
        return types.PointerType(types.ConstType(types.CHAR))


@util.dataclass
class GetVariable(Expression):
    var: Declaration

    def _get_type(self, scope):
        return self.var.type


@util.dataclass
class SetVariable(Expression):
    var: Declaration
    expr: Expression

    def _get_type(self, scope):
        return self.var.type


@util.dataclass
class FunctionCall(Expression):
    name: str
    args: typing.List[Expression]
    _decl = None  # FunctionDeclaration

    def _get_type(self, scope):
        decl = scope.get(self.name, [self.mark])
        if not isinstance(decl, FunctionDeclaration):
            raise errors.TypeError(
                [self.mark, decl.mark],
                f'{self.name} is not a function',
            )
        self._check_params(decl)
        return decl.rtype

    def _check_params(self, decl):
        if decl.varargs:
            if len(decl.params) < len(self.args):
                raise errors.TypeError(
                    [self.mark, decl.mark],
                    f'Expected at least {len(decl.params)} args '
                    f'but got {len(self.args)} args.'
                )
        else:
            if len(decl.params) != len(self.args):
                raise errors.TypeError(
                    [self.mark, decl.mark],
                    f'Expected {len(decl.params)} args '
                    f'but got {len(self.args)} args.'
                )
        for param, arg in zip(decl.params, self.args):
            if not types.convertible(arg.type, param.type):
                raise errors.TypeError(
                    [arg.mark, param.mark],
                    f'Expected type {param.type} but got {arg.type}',
                )

