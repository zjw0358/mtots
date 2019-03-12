from . import cst as cst_
from .scopes import Scope
from mtots.text import base
from mtots.util import dataclasses
from mtots.util import typing
from mtots.util.dataclasses import dataclass


class Type:
    def usable_as(self, other_type):
        return self is other_type


@typing.enforce
@dataclass(frozen=True)
class PrimitiveType(Type):
    name: str

    def __str__(self):
        return f'(primitive-type {self.name})'


VOID = PrimitiveType('void')
BOOL = PrimitiveType('bool')
INT = PrimitiveType('int')
DOUBLE = PrimitiveType('double')
STRING = PrimitiveType('string')


@dataclass
class Markable:
    mark: typing.Optional[base.Mark] = dataclasses.field(
        compare=False,
        repr=False,
    )


@dataclass
class TypeParameter(Type, Markable):
    name: str
    base: typing.Optional[Type] = dataclasses.field(
        repr=False,
    )

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return id(self)

    def __str__(self):
        if self.base is None:
            return f'(type-param {self.name})'
        else:
            return f'(type-param {self.name}: {self.base})'


@dataclass(frozen=True)
class Expression(base.Node):
    type: Type


@typing.enforce
@dataclass
class Field(Markable):
    type: Type
    name: str


@dataclass
class Class(Type, Markable):
    cst: cst_.Class = dataclasses.field(repr=False, compare=False)
    native: bool
    scope: Scope
    name: str
    base: typing.Optional[Type]
    type_parameters: typing.Optional[typing.List[TypeParameter]]
    generic: bool
    fields: typing.Dict[str, Field]

    def usable_as(self, other_cls):
        if not isinstance(other_cls, Class):
            return False

        while self is not None and self is not other_cls:
            self = self.base
        return self is other_cls

    def __str__(self):
        return f'(class {self.name})'


@dataclass
class ReifiedType(Type, Markable):
    class_: Class
    type_arguments: typing.List[Type]


@dataclass
class Parameter(Markable):
    type: Type
    name: str


@dataclass
class Function(Markable):
    cst: cst_.Function = dataclasses.field(repr=False, compare=False)
    scope: Scope
    native: bool
    return_type: Type
    name: str
    type_parameters: typing.Optional[typing.List[TypeParameter]]
    generic: bool
    parameters: typing.List[Parameter]
    body: typing.Optional[Expression]


##############################################################################
# Expressions
##############################################################################


@typing.enforce
@dataclass(frozen=True)
class Block(Expression):
    expressions: typing.Tuple[Expression, ...]


@typing.enforce
@dataclass(frozen=True)
class Int(Expression):
    value: int


@typing.enforce
@dataclass(frozen=True)
class String(Expression):
    value: str


@typing.enforce
@dataclass(frozen=True)
class FunctionCall(Expression):
    function: Function
    type_arguments: typing.Optional[typing.Tuple[Type, ...]]
    arguments: typing.Tuple[Expression, ...]
