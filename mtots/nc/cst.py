from mtots.parser import base
from mtots.util.dataclasses import dataclass
from mtots.util import typing


class Node(base.Node):
    pass


class FileLevelStatement(Node):
    pass


class TypeExpression(Node):
    pass


class ValueExpression(Node):
    pass


@typing.enforce
@dataclass(frozen=True)
class LineComment(Node):
    text: str


@typing.enforce
@dataclass(frozen=True)
class File(Node):
    statements: typing.Tuple[typing.Union[
        FileLevelStatement,
        LineComment,
    ], ...]


@typing.enforce
@dataclass(frozen=True)
class Inline(FileLevelStatement):
    name: str
    type: str
    text: str


@typing.enforce
@dataclass(frozen=True)
class Import(FileLevelStatement):
    module: str
    name: str
    alias: typing.Optional[str]


@typing.enforce
@dataclass(frozen=True)
class TypeParameter(Node):
    name: str
    base: typing.Optional[TypeExpression]


@typing.enforce
@dataclass(frozen=True)
class Parameter(Node):
    type: TypeExpression
    name: str


@typing.enforce
@dataclass(frozen=True)
class Function(FileLevelStatement):
    native: bool
    return_type: TypeExpression
    name: str
    type_parameters: typing.Optional[typing.Tuple[TypeParameter, ...]]
    parameters: typing.Tuple[Parameter, ...]
    body: typing.Optional[ValueExpression]


@typing.enforce
@dataclass(frozen=True)
class Field(Node):
    type: TypeExpression
    name: str


@typing.enforce
@dataclass(frozen=True)
class Method(FileLevelStatement):
    abstract: bool
    return_type: TypeExpression
    name: str
    parameters: typing.Tuple[Parameter, ...]
    body: typing.Optional[ValueExpression]


@typing.enforce
@dataclass(frozen=True)
class Class(FileLevelStatement):
    native: bool
    is_trait: bool
    name: str
    type_parameters: typing.Optional[typing.Tuple[TypeParameter, ...]]
    base: typing.Optional[TypeExpression]
    fields_and_methods: typing.Tuple[typing.Union[
        Field,
        Method,
        LineComment,
    ], ...]

    @property
    def fields(self):
        return tuple(
            m for m in self.fields_and_methods if isinstance(m, Field))

    @property
    def methods(self):
        return tuple(
            m for m in self.fields_and_methods if isinstance(m, Method))


@typing.enforce
@dataclass(frozen=True)
class VoidType(TypeExpression):
    pass


@typing.enforce
@dataclass(frozen=True)
class BoolType(TypeExpression):
    pass


@typing.enforce
@dataclass(frozen=True)
class IntType(TypeExpression):
    pass


@typing.enforce
@dataclass(frozen=True)
class DoubleType(TypeExpression):
    pass


@typing.enforce
@dataclass(frozen=True)
class StringType(TypeExpression):
    pass


@typing.enforce
@dataclass(frozen=True)
class Typename(TypeExpression):
    name: str


@typing.enforce
@dataclass(frozen=True)
class ReifiedType(TypeExpression):
    name: str
    type_arguments: typing.Tuple[TypeExpression, ...]


@typing.enforce
@dataclass(frozen=True)
class LocalVariableDeclaration(Node):
    type: typing.Optional[TypeExpression]
    name: str
    expression: ValueExpression


@typing.enforce
@dataclass(frozen=True)
class Block(ValueExpression):
    expressions: typing.Tuple[typing.Union[
        ValueExpression,
        LocalVariableDeclaration,
        LineComment,
    ], ...]


@typing.enforce
@dataclass(frozen=True)
class Bool(ValueExpression):
    value: bool


@typing.enforce
@dataclass(frozen=True)
class Int(ValueExpression):
    value: int


@typing.enforce
@dataclass(frozen=True)
class Double(ValueExpression):
    value: float


@typing.enforce
@dataclass(frozen=True)
class String(ValueExpression):
    value: str


@typing.enforce
@dataclass(frozen=True)
class Name(ValueExpression):
    value: str


@typing.enforce
@dataclass(frozen=True)
class FunctionCall(ValueExpression):
    name: str
    type_arguments: typing.Optional[typing.Tuple[TypeExpression, ...]]
    arguments: typing.Tuple[ValueExpression, ...]


@typing.enforce
@dataclass(frozen=True)
class MethodCall(ValueExpression):
    owner: ValueExpression
    name: str
    arguments: typing.Tuple[ValueExpression, ...]


@typing.enforce
@dataclass(frozen=True)
class New(ValueExpression):
    type: TypeExpression

