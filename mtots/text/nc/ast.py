from .rstates import NoReturn
from .rstates import Returns
from .rstates import ReturnState
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


@util.dataclass
class Source(Node):
    "Like Header, but FunctionDefinitions are properly parsed"
    imports: typing.List[BaseImport]
    decls: typing.List[GlobalDeclaration]


class Definition(Declaration):
    pass


@util.dataclass
class Field(Node):
    name: str
    type: Type


@util.dataclass
class StructDeclaration(GlobalDeclaration):
    pass


@util.dataclass
class StructDefinition(StructDeclaration, Definition):
    native: bool  # indicates if this struct is already defined in C code
    fields: typing.List[Field]


@util.dataclass
class Param(VariableDeclaration, Definition):
    name: str
    type: Type


@util.dataclass
class FunctionDeclaration(GlobalDeclaration):
    params: typing.List['Param']
    varargs: bool
    attrs: typing.List[str]
    rtype: Type


@util.dataclass
class FunctionDefinition(FunctionDeclaration, Definition):
    body: 'Block'


class Statement(Node, metaclass=abc.ABCMeta):
    _rstates = None  # return states

    @property
    def rstates(self) -> typing.Set[ReturnState]:
        if self._rstates is None:
            self._rstates = frozenset(self._get_return_states())
        return self._rstates

    @abc.abstractmethod
    def _get_return_states(self):
        pass


class Expression(Node, metaclass=abc.ABCMeta):
    _type = None

    @property
    def type(self):
        if self._type is None:
            self._type = self._get_type()
        return self._type

    @abc.abstractmethod
    def _get_type(self):
        pass


@util.dataclass
class ExpressionStatement(Statement):
    expr: Expression

    def _get_return_states(self):
        return {NoReturn()}


@util.dataclass
class If(Statement):
    cond: Expression
    body: Statement
    other: typing.Optional[Statement]

    def _get_return_states(self):
        return (
            self.body.rstates |
            (self.other.rstates if self.other else {NoReturn()})
        )


@util.dataclass
class While(Statement):
    cond: Expression
    body: Statement

    def _get_return_states(self):
        return {NoReturn()} | self.body.rstates


@util.dataclass
class Return(Statement):
    expr: typing.Optional[Expression]

    def _get_return_states(self):
        return {Returns(self.expr.type)}


@util.dataclass
class Block(Statement):
    stmts: typing.List[Statement]

    def _get_return_states(self):
        nr = NoReturn()
        stmts = self.stmts
        rstates = {nr}
        for i, stmt in enumerate(stmts):
            if i and nr not in stmt[i - 1].rstates:
                raise base.Error([stmt.mark], f'Unrechable statement')
            rstates |= stmt.rstates
        if nr not in stmts[len(stmts) - 1].rstates:
            rstates.discard(nr)
        return rstates


@util.dataclass
class GetVariable(Expression):
    var: Declaration

    def _get_type(self):
        return self.var.type


@util.dataclass
class SetVariable(Expression):
    var: Declaration
    expr: Expression

    def _get_type(self):
        return self.var.type


@util.dataclass
class FunctionCall(Expression):
    decl: FunctionDeclaration
    args: typing.List[Expression]

