from mtots.text import base
from mtots.util.dataclasses import dataclass
import typing


Node = base.Node


class TypeReference:
    pass


@dataclass(frozen=True)
class SimpleType(TypeReference):
    name: str


@dataclass(frozen=True)
class ListType(TypeReference):
    base: TypeReference


@dataclass(frozen=True)
class StructType(TypeReference):
    name: str

@dataclass(frozen=True)
class TupleType(TypeReference):
    subtypes: typing.List[TypeReference]


@dataclass(frozen=True)
class FunctionType(TypeReference):
    return_type: TypeReference
    parameter_types: typing.List[TypeReference]


@dataclass(frozen=True)
class Definition(Node):
    module_name: str
    native: bool
    short_name: str

    @property
    def qualified_name(self):
        return f'{self.module_name}#{self.short_name}'


@dataclass(frozen=True)
class Import(Node):
    name: str
    alias: str


@dataclass(frozen=True)
class Module(Node):
    name: str
    imports: typing.List[Import]
    definitions: typing.List[Definition]


class Statement(Node):
    pass


@dataclass(frozen=True)
class Block(Statement):
    statements: typing.List[Statement]


@dataclass(frozen=True)
class Field(Node):
    type: TypeReference
    name: str


@dataclass(frozen=True)
class Struct(Definition):
    fields: typing.Optional[typing.List[Field]]


@dataclass(frozen=True)
class Parameter(Node):
    type: TypeReference
    name: str


@dataclass(frozen=True)
class FunctionDefinition(Definition):
    parameters: typing.List[Parameter]
    return_type: TypeReference
    body: typing.Optional[Block]


class Expression(Node):
    pass
