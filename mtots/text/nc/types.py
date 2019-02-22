from mtots import util
import typing


class Type:
    pass


@util.dataclass
class _PrimitiveType(Type):
    name: str


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
    rtype: Type                # return type
    attrs: typing.List[str]    # attributes (e.g. calling convention)
    ptypes: typing.List[Type]  # parameter types
    varargs: bool              # whether varargs are accepted

# Primitive types
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


@util.multimethod(2)
def convertible(builder):

    @builder.on(PointerType, PointerType)
    def convertible(source, dest):
        return source == dest or dest.type == VOID

    @builder.on(Type, Type)
    def convertible(source, dest):
        return source == dest
