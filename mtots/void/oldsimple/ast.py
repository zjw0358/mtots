from mtots import util
from mtots.util import dataclasses
from mtots.util import typing
from mtots.parser import base


class Type:
    pass


@util.dataclass(frozen=True)
class _PrimitiveType(Type):
    name: str


@util.dataclass
class Markable:
    mark: typing.Optional[base.Mark] = dataclasses.field(
        compare=False,
        repr=False,
    )


class Expression(Markable):
    pass


class _Class(Type, Markable):
    pass


class _Function(Markable):
    pass


@util.dataclass
class GenericType(Type):
    class_: _Class
    type_arguments: typing.List[Type]


@util.dataclass(frozen=True)
class TypeParameter:
    owner: typing.Union[_Class, _Function]
    name: str
    type: Type


VOID = _PrimitiveType('void')
INT = _PrimitiveType('int')
DOUBLE = _PrimitiveType('double')
STRING = _PrimitiveType('string')


@util.dataclass
class Field(Markable):
    owner: _Class
    name: str
    type: Type


@util.dataclass
class Class(_Class):
    native: bool
    module: util.Scope
    short_name: str
    type_parameters: typing.Optional[typing.List[TypeParameter]]
    base: typing.Optional[_Class]
    fields: typing.Dict[str, Field]


@util.dataclass
class Parameter(Markable):
    owner: typing.Union[_Class, _Function]
    name: str
    type: Type


@util.dataclass
class Function(_Function):
    native: bool
    module: util.Scope
    short_name: str
    type_parameters: typing.Optional[typing.List[TypeParameter]]
    parameters: typing.List[Parameter]
    body: typing.Optional[Expression]

