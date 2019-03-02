from mtots import util
import typing

@util.dataclass(frozen=True)
class Type:
    @property
    def is_primitive(self):
        return False


@util.dataclass(frozen=True)
class _PrimitiveType(Type):
    name: str

    @property
    def is_primitive(self):
        return True

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
    rtype: Type                      # return type
    attrs: typing.Tuple[str, ...]    # attributes (e.g. calling convention)
    ptypes: typing.Tuple[Type, ...]  # parameter types
    varargs: bool                    # whether varargs are accepted
