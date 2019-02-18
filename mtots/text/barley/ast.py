from mtots.text import base
from mtots.util.dataclasses import dataclass
import typing


Node = base.Node


class TypeReference:
    pass


@dataclass
class SimpleType(TypeReference):
    name: str


@dataclass
class ListType(TypeReference):
    base: TypeReference


@dataclass
class StructType(TypeReference):
    name: str

@dataclass
class TupleType(TypeReference):
    subtypes: typing.List[TypeReference]


@dataclass
class FunctionType(TypeReference):
    return_type: TypeReference
    parameter_types: typing.List[TypeReference]


@dataclass
class Definition(Node):
    module_name: str
    native: bool
    short_name: str

    @property
    def qualified_name(self):
        return f'{self.module_name}#{self.short_name}'


@dataclass
class Import(Node):
    name: str
    alias: str


@dataclass
class Module(Node):
    name: str
    imports: typing.List[Import]
    definitions: typing.List[Definition]


class Statement(Node):
    pass


@dataclass
class Block(Statement):
    statements: typing.List[Statement]


@dataclass
class Field(Node):
    type: TypeReference
    name: str


@dataclass
class Struct(Definition):
    fields: typing.Optional[typing.List[Field]]


@dataclass
class Parameter(Node):
    type: TypeReference
    name: str


@dataclass
class FunctionDefinition(Definition):
    parameters: typing.List[Parameter]
    return_type: TypeReference
    body: typing.Optional[Block]


class Expression(Node):
    pass
