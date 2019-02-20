from mtots import util
import typing


class Type:
    pass


@util.dataclass
class SimpleType(Type):
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
    rtype: Type                # return type
    attrs: typing.List[str]    # attributes (e.g. calling convention)

