from . import types
from .types import Type
from mtots import util
from mtots.text import base
from mtots.util import dataclasses
from mtots.util import typing


# Name of the module that is always implicitly included
PRELUDE = 'prelude'

# Set of symbols that are implicitly imported in all
# modules but PRELUDE itself
PRELUDE_SYMBOLS = {
    'Object',
    'print',
    'String',
}

# Name of the ancestor of all classes
OBJECT = f'{PRELUDE}.Object'


STRING = f'{PRELUDE}.String'


@util.dataclass(frozen=True)
class Node(base.Node):
    pass


@util.dataclass(frozen=True)
class Module(Node):
    name: str
    imports: typing.Tuple['Import', ...]
    vars: typing.Tuple['GlobalVariable', ...]
    funcs: typing.Tuple['Function', ...]
    clss: typing.Tuple['Class', ...]


@util.dataclass(frozen=True)
class Import(Node):
    name: str  # fully qualified name
    alias: str

    @property
    def module(self):
        assert '.' in self.name
        return '.'.join(self.name.split('.')[:-1])


@util.dataclass(frozen=True)
class GlobalVariable(Node):
    type: Type
    name: str  # fully qualified name
    expr: 'Expression'


@util.dataclass(frozen=True)
class Function(Node):
    rtype: Type
    name: str  # fully qualified name
    params: typing.Tuple['Parameter', ...]
    body: 'Block'

    @property
    def native(self):
        return self.body is None


@util.dataclass(frozen=True)
class Class(Node):
    native: bool
    name: str  # fully qualified name
    base: typing.Optional[str]  # fully qualified name
    fields: typing.Tuple['Field', ...]
    methods: typing.Tuple['Method', ...]


@util.dataclass(frozen=True)
class Parameter(Node):
    type: Type
    name: str


@util.dataclass(frozen=True)
class Field(Node):
    type: Type
    name: str


@util.dataclass(frozen=True)
class Method(Node):
    rtype: Type
    name: str  # local name
    params: typing.Tuple[Parameter, ...]
    body: 'Block'


@util.dataclass(frozen=True)
class Statement(Node):
    pass


@util.dataclass(frozen=True)
class Expression(Node):
    pass


@util.dataclass(frozen=True)
class ExpressionStatement(Statement):
    expr: Expression


@util.dataclass(frozen=True)
class Return(Statement):
    expr: typing.Optional[Expression]


@util.dataclass(frozen=True)
class Block(Statement):
    stmts: typing.Tuple[Statement, ...]


@util.dataclass(frozen=True)
class IntLiteral(Expression):
    value: int
    type = types.INT


@util.dataclass(frozen=True)
class StringLiteral(Expression):
    value: str
    type = types.ClassType(STRING)


@util.dataclass(frozen=True)
class FunctionCall(Expression):
    f: Function
    args: typing.Tuple[Expression, ...]

