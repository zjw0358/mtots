from mtots.text import base
from mtots.util.dataclasses import dataclass
from typing import List
from typing import Optional


Node = base.Node


@dataclass
class Module(Node):
    name: str
    definitions: List['Definition']


@dataclass
class Definition(Node):
    module_name: str
    short_name: str

    @property
    def qualified_name(self):
        return f'{self.module_name}.{self.short_name}'


@dataclass
class FunctionDefinition(Definition):
    type_params: Optional[List['TypeParameter']]
    params: List['Parameter']
    return_type: 'TypeReference'
    body: 'Block'


@dataclass
class TypeReference(Node):
    name: str
    args: Optional[List['TypeReference']]


class Statement(Node):
    pass


@dataclass
class Block(Statement):
    stmts: List[Statement]


class Expression(Node):
    pass
