from mtots import util
from mtots.text import base
from mtots.util import dataclasses
from mtots.util import typing


class Type:
    pass


@util.dataclass(frozen=True)
class _PrimitiveType(Type):
    name: str

    def __repr__(self):
        return self.name.upper()


@util.dataclass(frozen=True)
class NamedType(Type):
    name: str

    def __str__(self):
        return self.name


@util.dataclass(frozen=True)
class PointerType(Type):
    type: Type

    def __str__(self):
        return f'{self.type}*'


@util.dataclass(frozen=True)
class ConstType(Type):
    type: Type

    def __str__(self):
        return f'{self.type} const'


@util.dataclass(frozen=True)
class FunctionType(Type):
    rtype: Type                # return type
    attrs: typing.List[str]    # attributes (e.g. calling convention)
    ptypes: typing.List[Type]  # parameter types
    varargs: bool              # whether varargs are accepted

    def __str__(self):
        rtype = str(self.rtype)
        attrs = f'[{" ".join(map(str, self.attrs))}]' if self.attrs else ''
        ptypes = ', '.join(map(str, self.ptypes))
        varargs = ', ...' if self.varargs else ''
        return f'{rtype}{attrs}({ptypes}{varargs})'

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
        return (
            source == dest or
            dest.type == VOID or
            (isinstance(dest.type, ConstType) and
                dest.type.type == source.type)
        )

    @builder.on(Type, Type)
    def convertible(source, dest):
        return source == dest
