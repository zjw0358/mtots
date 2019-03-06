from .dataclasses import dataclass
import typing


class FakeType:
    pass


@dataclass(frozen=True)
class TupleType(FakeType):

    def __getitem__(self, *types):
        if types and types[-1] == ...:
            subtype, _ = types
            return SequenceTupleType(subtype)
        else:
            return GenericTupleType(types=types)

    def __instancecheck__(self, instance):
        return isinstance(tuple, instance)

    def __repr__(self):
        return 'typing.Tuple'


@dataclass(frozen=True)
class GenericTupleType(FakeType):
    types: tuple

    def __instancecheck__(self, instance):
        return (isinstance(instance, tuple) and
                len(self.types) == len(instance) and
                all(isinstance(x, t) for t, x in zip(self.types, instance)))

    def __repr__(self):
        return f'typing.Tuple[{", ".join(map(repr, self.types))}]'


@dataclass(frozen=True)
class SequenceTupleType(FakeType):
    type: type

    def __instancecheck__(self, instance):
        return (isinstance(instance, tuple) and
                all(isinstance(x, self.type) for x in instance))

    def __repr__(self):
        return f'typing.Tuple[{repr(self.type)}, ...]'


@dataclass(frozen=True)
class ListType(FakeType):

    def __getitem__(self, subtype):
        return GenericListType(subtype)

    def __instancecheck__(self, instance):
        return isinstance(instance, list)

    def __repr__(self):
        return 'typing.List'


@dataclass(frozen=True)
class GenericListType(FakeType):
    type: type

    def __instancecheck__(self, instance):
        return (isinstance(instance, list) and
                all(isinstance(x, self.type) for x in instance))

    def __repr__(self):
        return f'typing.List[{repr(self.type)}]'


@dataclass(frozen=True)
class OptionalType(FakeType):
    def __getitem__(self, subtype):
        return GenericOptionalType(subtype)

    def __instancecheck__(self, instance):
        return True

    def __repr__(self):
        return 'typing.Optional'


@dataclass(frozen=True)
class GenericOptionalType(FakeType):
    type: type

    def __instancecheck__(self, instance):
        return instance is None or isinstance(instance, self.type)

    def __repr__(self):
        return f'typing.Optional[{repr(self.type)}]'


Tuple = TupleType()
List = ListType()
Optional = OptionalType()
Pattern = typing.Pattern
Match = typing.Match
Callable = typing.Callable
Iterable = typing.Iterable
Iterator = typing.Iterator
Union = typing.Union
Set = typing.Set
Dict = typing.Dict
NamedTuple = typing.NamedTuple
