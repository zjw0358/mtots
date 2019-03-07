from mtots.text import base
from mtots.util.dataclasses import dataclass
from mtots.util import typing


class Node(base.Node):
    pass


class ModuleLevelStatement(Node):
    pass


class TypeExpression(Node):
    pass


class ValueExpression(Node):
    pass


@typing.enforce
@dataclass(frozen=True)
class Module(Node):
    statements: typing.Tuple[ModuleLevelStatement, ...]


@typing.enforce
@dataclass(frozen=True)
class TypeParameter(Node):
    name: str
    base: typing.Optional[TypeExpression]


@typing.enforce
@dataclass(frozen=True)
class GlobalVariable(ModuleLevelStatement):
    name: str
    type: TypeExpression


@typing.enforce
@dataclass(frozen=True)
class Parameter(Node):
    name: str
    type: TypeExpression


@typing.enforce
@dataclass(frozen=True)
class Function(ModuleLevelStatement):
    native: bool
    name: str
    type_parameters: typing.Optional[typing.Tuple[TypeParameter, ...]]
    parameters: typing.Tuple[Parameter, ...]
    return_type: TypeExpression
    body: typing.Optional[ValueExpression]


class ClassMember(Node):
    pass


@typing.enforce
@dataclass(frozen=True)
class Class(ModuleLevelStatement):
    native: bool
    name: str
    type_parameters: typing.Optional[typing.Tuple[TypeParameter, ...]]
    base: typing.Optional[TypeExpression]
    members: typing.Tuple[ClassMember, ...]


@typing.enforce
@dataclass(frozen=True)
class Field(ClassMember):
    name: str
    type: TypeExpression


@dataclass(frozen=True)
class VoidType(TypeExpression):
    pass


@dataclass(frozen=True)
class IntType(TypeExpression):
    pass


@dataclass(frozen=True)
class DoubleType(TypeExpression):
    pass


@dataclass(frozen=True)
class StringType(TypeExpression):
    pass


@typing.enforce
@dataclass(frozen=True)
class Typename(TypeExpression):
    name: str


@typing.enforce
@dataclass(frozen=True)
class GenericType(TypeExpression):
    name: str
    types: typing.Tuple[TypeExpression, ...]


@typing.enforce
@dataclass(frozen=True)
class Block(ValueExpression):
    expressions: typing.Tuple[ValueExpression, ...]


