from . import types
from mtots import util
from mtots.text import base
from mtots.util import dataclasses
from mtots.util import typing


@typing.check
@util.dataclass(frozen=True)
class Node(base.Node):
    pass


########################################################################
# TOP LEVEL CONCEPTS (Almost serves as TOC)
########################################################################


@typing.check
@util.dataclass(frozen=True)
class GlobalStatement(Node):
    pass


@typing.check
@util.dataclass(frozen=True)
class Statement(Node):
    pass


@typing.check
@util.dataclass(frozen=True)
class Block(Statement):
    stmts: typing.Tuple[Statement, ...]


@typing.check
@util.dataclass(frozen=True)
class Expression(Node):
    type: types.Type


@typing.check
@util.dataclass(frozen=True)
class TranslationUnit(Node):
    stmts: typing.Tuple[GlobalStatement, ...]


########################################################################
# GLOBAL STATEMENTS
########################################################################


@typing.check
@util.dataclass(frozen=True)
class InlineBlob(GlobalStatement):
    type: str
    text: str


@typing.check
@util.dataclass(frozen=True)
class Import(GlobalStatement):
    path: str
    tu: TranslationUnit = dataclasses.field(compare=False, repr=False)


@typing.check
@util.dataclass(frozen=True)
class NativeTypedef(GlobalStatement):
    name: str


@typing.check
@util.dataclass(frozen=True)
class GlobalVariableDeclaration(GlobalStatement):
    native: bool
    type: types.Type
    name: str


@typing.check
@util.dataclass(frozen=True)
class Field(Node):
    type: types.Type
    name: str


@typing.check
@util.dataclass(frozen=True)
class StructDefinition(GlobalStatement):
    native: bool
    typedef: bool
    name: str
    fields: typing.Tuple[Field, ...]


@typing.check
@util.dataclass(frozen=True)
class Parameter(Node):
    type: types.Type
    name: str


@typing.check
@util.dataclass(frozen=True)
class FunctionPrototype(Node):
    native: bool
    rtype: types.Type
    name: str
    params: typing.Tuple[Parameter, ...]
    varargs: bool

    @property
    def type(self):
        return types.FunctionType(
            rtype=self.rtype,
            ptypes=tuple(p.type for p in self.params),
            varargs=self.varargs,
        )


@typing.check
@util.dataclass(frozen=True)
class FunctionDefinition(GlobalStatement):
    proto: FunctionPrototype
    body: typing.Optional[Block]

    @property
    def native(self):
        return self.proto.native

    @property
    def rtype(self):
        return self.proto.rtype

    @property
    def name(self):
        return self.proto.name

    @property
    def params(self):
        return self.proto.params

    @property
    def varargs(self):
        return self.proto.varargs


########################################################################
# Statements
########################################################################


@typing.check
@util.dataclass(frozen=True)
class LocalVariableDeclaration(Statement):
    type: types.Type
    name: str
    expr: typing.Optional[Expression]


@typing.check
@util.dataclass(frozen=True)
class Return(Statement):
    expr: Expression


@typing.check
@util.dataclass(frozen=True)
class ExpressionStatement(Statement):
    expr: Expression


########################################################################
# Expressions
########################################################################


@typing.check
@util.dataclass(frozen=True)
class FunctionName(Expression):
    proto: FunctionPrototype

    @property
    def name(self):
        return self.proto.name


@typing.check
@util.dataclass(frozen=True)
class LocalVariable(Expression):
    decl: typing.Union[LocalVariableDeclaration, Parameter]

    @property
    def name(self):
        return self.decl.name


@typing.check
@util.dataclass(frozen=True)
class IntLiteral(Expression):
    value: int


@typing.check
@util.dataclass(frozen=True)
class DoubleLiteral(Expression):
    value: float


@typing.check
@util.dataclass(frozen=True)
class StringLiteral(Expression):
    value: str


@typing.check
@util.dataclass(frozen=True)
class FunctionCall(Expression):
    f: Expression
    args: typing.Tuple[Expression, ...]
