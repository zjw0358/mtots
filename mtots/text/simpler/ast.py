from . import cst
from mtots.text import base
from mtots.util import dataclasses
from mtots.util import typing
from mtots.util.dataclasses import dataclass


class Type:
    pass


@typing.enforce
@dataclass(frozen=True)
class PrimitiveType(Type):
    name: str


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


class Expression(Markable):
    pass


@typing.enforce
@dataclass
class Field(Markable):
    type: Type
    name: str


@dataclass
class Class(Type, Markable):
    cst: cst.Class
    complete: bool
    native: bool
    name: str
    base: typing.Optional[Type]
    type_parameters: typing.Optional[typing.List[TypeParameter]]
    generic: bool
    fields: typing.Dict[str, Field]


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
    complete: bool
    native: bool
    return_type: Type
    name: str
    type_parameters: typing.Optional[typing.List[TypeParameter]]
    generic: bool
    parameters: typing.List[Parameter]
    body: typing.Optional[Expression]

