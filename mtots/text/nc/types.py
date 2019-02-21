from mtots import util
import typing


class Type:
    pass


@util.dataclass
class NamedType(Type):
    name: str


@util.dataclass
class PointerType(Type):
    type: Type


@util.dataclass
class ConstType(Type):
    type: Type


@util.dataclass
class FunctionType(Type):
    ptypes: typing.List[Type]  # parameter types
    varargs: bool              # whether varargs are accepted
    attrs: typing.List[str]    # attributes (e.g. calling convention)
    rtype: Type                # return type

# Primitive types
VOID = NamedType('void')
CHAR = NamedType('char')
SIGNED_CHAR = NamedType('signed char')
UNSIGNED_CHAR = NamedType('unsigned char')
SHORT = NamedType('short')
UNSIGNED_SHORT = NamedType('unsigned short')
INT = NamedType('int')
UNSIGNED_INT = NamedType('unsigned int')
LONG = NamedType('long')
UNSIGNED_LONG = NamedType('unsigned long')
LONG_LONG = NamedType('long long')
UNSIGNED_LONG_LONG = NamedType('unsigned long long')
FLOAT = NamedType('float')
DOUBLE = NamedType('double')
LONG_DOUBLE = NamedType('long double')
