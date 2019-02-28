from mtots import util


@util.dataclass(frozen=True)
class Type:
    pass


@util.dataclass(frozen=True)
class _PrimitiveType(Type):
    name: str

    def __repr__(self):
        return self.name.upper()


VOID = _PrimitiveType('void')
INT = _PrimitiveType('int')
DOUBLE = _PrimitiveType('double')


@util.dataclass(frozen=True)
class ClassType(Type):
    name: str

    def __repr__(self):
        return self.name


@util.multimethod(2)
def convertible(builder):

    @builder.on(ClassType, ClassType)
    def c(a, b, global_dict):
        "a is convertible to b, iff a is a descendant class of b"
        a_name = a.name
        b_name = b.name
        while a_name is not None and a_name != b_name:
            a_name = global_dict[a_name].base
        return a_name == b_name

    @builder.on(Type, Type)
    def c(a, b, global_dict):
        return a == b
