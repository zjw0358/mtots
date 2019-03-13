from mtots import util
from mtots.text import base
from mtots.util import dataclasses
from . import types
from mtots.util import typing


@util.dataclass(frozen=True)
class Node(base.Node):
    pass


########################################################################
# TOP LEVEL CONCEPTS (Almost serves as TOC)
########################################################################


@util.dataclass(frozen=True)
class GlobalStatement(Node):
    pass


@util.dataclass(frozen=True)
class TypeReference(Node):
    pass


@util.dataclass(frozen=True)
class Statement(Node):
    pass


@util.dataclass(frozen=True)
class Block(Statement):
    stmts: typing.Tuple[Statement, ...]


@util.dataclass(frozen=True)
class Expression(Node):
    pass


@util.dataclass(frozen=True)
class TranslationUnit(Node):
    stmts: typing.Tuple[GlobalStatement, ...]


########################################################################
# GLOBAL STATEMENTS
########################################################################


@util.dataclass(frozen=True)
class InlineBlob(GlobalStatement):
    type: str
    text: str


@util.dataclass(frozen=True)
class Import(GlobalStatement):
    path: str


@util.dataclass(frozen=True)
class NativeTypedef(GlobalStatement):
    name: str


@util.dataclass(frozen=True)
class GlobalVariableDeclaration(GlobalStatement):
    native: bool
    type: TypeReference
    name: str


@util.dataclass(frozen=True)
class Field(Node):
    type: TypeReference
    name: str


@util.dataclass(frozen=True)
class StructDefinition(GlobalStatement):
    native: bool
    typedef: bool
    name: str
    fields: typing.Tuple[Field, ...]


@util.dataclass(frozen=True)
class Parameter(Node):
    type: TypeReference
    name: str


@util.dataclass(frozen=True)
class FunctionDefinition(GlobalStatement):
    rtype: TypeReference
    name: str
    params: typing.Tuple[Parameter, ...]
    varargs: bool
    body: typing.Optional[Block]

    @property
    def native(self):
        return self.body is None


########################################################################
# TYPES
########################################################################


@util.dataclass(frozen=True)
class PrimitiveType(TypeReference):
    type: types.Type


@util.dataclass(frozen=True)
class NamedType(TypeReference):
    name: str


@util.dataclass(frozen=True)
class PointerType(TypeReference):
    type: TypeReference


@util.dataclass(frozen=True)
class ConstType(TypeReference):
    type: TypeReference


@util.dataclass(frozen=True)
class FunctionType(TypeReference):
    rtype: TypeReference                      # return type
    ptypes: typing.Tuple[TypeReference, ...]  # parameter types
    varargs: bool                             # ...


########################################################################
# Statements
########################################################################


@util.dataclass(frozen=True)
class LocalVariableDeclaration(Statement):
    type: TypeReference
    name: str
    expr: typing.Optional[Expression]


@util.dataclass(frozen=True)
class Return(Statement):
    expr: Expression


@util.dataclass(frozen=True)
class ExpressionStatement(Statement):
    expr: Expression


########################################################################
# Expressions
########################################################################


@util.dataclass(frozen=True)
class Variable(Expression):
    name: str


@util.dataclass(frozen=True)
class IntLiteral(Expression):
    value: int


@util.dataclass(frozen=True)
class DoubleLiteral(Expression):
    value: float


@util.dataclass(frozen=True)
class StringLiteral(Expression):
    value: str


@util.dataclass(frozen=True)
class FunctionCall(Expression):
    f: Expression
    args: typing.Tuple[Expression, ...]


@util.dataclass(frozen=True)
class Unop(Expression):
    op: str
    expr: Expression


@util.dataclass(frozen=True)
class Binop(Expression):
    left: Expression
    op: str
    right: Expression

