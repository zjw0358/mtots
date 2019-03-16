"""
"""
from mtots import test
from mtots import util
from mtots.parser import base
from mtots.util import typing
from enum import Enum
from enum import auto


def dataclass(cls):
    return typing.enforce(util.dataclass(frozen=True)(cls))


class Node(base.Node):
    pass


class Suite(Node):
    pass


class Expression(Node):
    pass


@dataclass
class Module(Node):
    suites: typing.Tuple[Suite, ...]


@dataclass
class Import(Suite):
    from_ : typing.Optional[str]
    name: str
    alias: typing.Optional[str]


@dataclass
class ExpressionSuite(Suite):
    expression: Expression


@dataclass
class Pass(Suite):
    pass


@dataclass
class Block(Suite):
    suites: typing.Tuple[Suite, ...]


@dataclass
class Class(Suite):
    decorators: typing.Tuple[Expression, ...]
    name: str
    base: typing.Optional[Expression]
    body: Block


class ParameterType(Enum):
    NORMAL = auto()
    VARARGS = auto()
    KWARGS = auto()


@dataclass
class Parameter(Node):
    type: ParameterType
    name: typing.Optional[str]
    default: typing.Optional[Expression]


@dataclass
class Function(Suite):
    decorators: typing.Tuple[Expression, ...]
    name: str
    parameters: typing.Tuple[Parameter, ...]
    body: Block
