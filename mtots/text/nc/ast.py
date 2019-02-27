from mtots import util
from mtots.text import base
from mtots.util import dataclasses
import typing


TUPLE = lambda type: typing.Tuple[type, ...]


#############
# types
#############


@util.dataclass(frozen=True)
class Type:
    pass


@util.dataclass(frozen=True)
class _PrimitiveType(Type):
    name: str

    def __repr__(self):
        return self.name.upper()

VOID = _PrimitiveType('void')
CHAR = _PrimitiveType('char')
SIGNED_CHAR = _PrimitiveType('signed char')
UNSIGNED_CHAR = _PrimitiveType('unsigned char')
SHORT = _PrimitiveType('short')
UNSIGNED_SHORT = _PrimitiveType('unsigned short')
INT = _PrimitiveType('int')
UNSIGNED_INT = _PrimitiveType('unsigned int')
LONG = _PrimitiveType('long')
UNSIGNED_LONG = _PrimitiveType('unsigned long')
LONG_LONG = _PrimitiveType('long long')
UNSIGNED_LONG_LONG = _PrimitiveType('unsigned long long')
FLOAT = _PrimitiveType('float')
DOUBLE = _PrimitiveType('double')
LONG_DOUBLE = _PrimitiveType('long double')


@util.dataclass(frozen=True)
class RawNameType(Type):
    """This is not a true type. This is a place-holder
    for when a name is not yet resolved.
    """
    name: str


@util.dataclass(frozen=True)
class NativeType(Type):
    """Unknown whether it is a struct type or some typedef,
    but declared in the raw C code, and not a native type.
    E.g. size_t.
    """
    name: str


@util.dataclass(frozen=True)
class StructType(Type):
    name: str


@util.dataclass(frozen=True)
class PointerType(Type):
    type: Type


@util.dataclass(frozen=True)
class ConstType(Type):
    type: Type


@util.dataclass(frozen=True)
class FunctionType(Type):
    rtype: Type                # return type
    attrs: TUPLE(str)          # attributes (e.g. calling convention)
    ptypes: TUPLE(Type)        # parameter types
    varargs: bool              # whether varargs are accepted


#############
# nodes
#############


@util.dataclass(frozen=True)
class Node(base.Node):
    pass


class GlobalStatement(Node):
    pass


@util.dataclass(frozen=True)
class Include(GlobalStatement):
    quotes: bool
    path: str


@util.dataclass(frozen=True)
class Import(GlobalStatement):
    path: str


@util.dataclass(frozen=True)
class NativeTypedef(GlobalStatement):
    name: str


class Statement(Node):
    pass


@util.dataclass(frozen=True)
class Block(Statement):
    stmts: TUPLE(Statement)


class Expression(Node):
    pass  # abstract field 'type'


class VariableDeclaration(Node):
    pass  # abstract fields 'type' and 'name'


@util.dataclass(frozen=True)
class Program(Node):
    stmts: TUPLE(GlobalStatement)


@util.dataclass(frozen=True)
class Field(Node):
    type: Type
    name: str


@util.dataclass(frozen=True)
class StructDefinition(GlobalStatement):
    native: str
    name: str
    fields: TUPLE(Field)


@util.dataclass(frozen=True)
class Parameter(VariableDeclaration, GlobalStatement):
    type: Type
    name: str


@util.dataclass(frozen=True)
class FunctionDefinition(GlobalStatement):
    native: bool
    rtype: Type
    name: str
    attrs: TUPLE(str)
    params: TUPLE(Parameter)
    varargs: bool
    body: Block


@util.dataclass(frozen=True)
class ExpressionStatement(Statement):
    expr: Expression


@util.dataclass(frozen=True)
class If(Statement):
    cond: Expression
    body: Statement
    other: typing.Optional[Statement]


@util.dataclass(frozen=True)
class While(Statement):
    cond: Expression
    body: Statement


@util.dataclass(frozen=True)
class Return(Statement):
    expr: typing.Optional[Expression]


@util.dataclass(frozen=True)
class IntLiteral(Expression):
    value: int
    type: Type = INT


@util.dataclass(frozen=True)
class StringLiteral(Expression):
    value: str
    type: Type = PointerType(ConstType(CHAR))


@util.dataclass(frozen=True)
class SyntacticFunctionCall(Expression):
    # unresolved function call
    # unresolved expressions don't need a 'type' field.
    f: Expression
    args: TUPLE(Expression)

