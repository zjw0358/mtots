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
    pass


class Statement(StatementOrExpression):
    # This is required of all 'Statement' subclasses,
    # but if we declare Statement a dataclass, we get
    # issues with creating constructor because of
    # default arguments being not allowed before
    # non-default arguments.
    rstates: typing.Set[ReturnState]


class Expression(StatementOrExpression):
    # This is required of all 'Expression' subclasses,
    # but if we declare Expression a dataclass, we get
    # issues with creating constructor because of
    # default arguments being not allowed before
    # non-default arguments.
    type: Type


@util.dataclass
class ExpressionStatement(Statement):
    expr: Expression
    rstates: typing.Set[ReturnState] = None


@util.dataclass
class If(Statement):
    cond: Expression
    body: Statement
    other: typing.Optional[Statement]
    rstates: typing.Set[ReturnState] = None


@util.dataclass
class While(Statement):
    cond: Expression
    body: Statement
    rstates: typing.Set[ReturnState] = None


@util.dataclass
class Return(Statement):
    expr: typing.Optional[Expression]
    rstates: typing.Set[ReturnState] = None


@util.dataclass
class Block(Statement):
    stmts: typing.List[Statement]
    rstates: typing.Set[ReturnState] = None


@util.dataclass
class IntLiteral(Expression):
    value: int
    type: Type = types.INT


@util.dataclass
class StringLiteral(Expression):
    value: str
    type: Type = types.PointerType(types.ConstType(types.CHAR))


@util.dataclass
class GetVariable(Expression):
    name: str
    var: Declaration = None
    type: Type = None


@util.dataclass
class SetVariable(Expression):
    name: str
    expr: Expression
    var: Declaration = None
    type: Type = None


@util.dataclass
class FunctionCall(Expression):
    name: str
    args: typing.List[Expression]
    decl: FunctionDeclaration = None
    type: Type = None
