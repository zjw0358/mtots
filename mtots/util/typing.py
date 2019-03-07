from .dataclasses import dataclass
from mtots import test
import functools
import typing


def enforce(cls):

    if hasattr(cls, '__annotations__'):
        init = cls.__init__
        @functools.wraps(init)
        def _check(self, *args, **kwargs):
            init(self, *args, **kwargs)
            for field_name, field_type in cls.__annotations__.items():
                if not isinstance(getattr(self, field_name), field_type):
                    raise TypeError(
                        f'Expected field {repr(field_name)} of {cls} '
                        f'to be {field_type} but got '
                        f'{repr(getattr(self, field_name))}')
        cls.__init__ = _check

    return cls



class FakeType:
    pass


@enforce
@dataclass(frozen=True)
class UnionType(FakeType):

    def __getitem__(self, types):
        if not isinstance(types, tuple):
            types = (types, )

        return GenericUnionType(types)

    def __instancecheck__(self, instance):
        return True

    def __repr__(self):
        return 'typing.Union'


@enforce
@dataclass(frozen=True)
class GenericUnionType(FakeType):
    types: tuple

    def __instancecheck__(self, instance):
        return any(isinstance(instance, t) for t in self.types)

    def __repr__(self):
        return f'typing.Union[{", ".join(map(repr, self.types))}]'


@enforce
@dataclass(frozen=True)
class TupleType(FakeType):

    def __getitem__(self, types):
        if not isinstance(types, tuple):
            types = (types, )

        if types and types[-1] == ...:
            subtype, _ = types
            return SequenceTupleType(subtype)
        else:
            return GenericTupleType(types=types)

    def __instancecheck__(self, instance):
        return isinstance(instance, tuple)

    def __repr__(self):
        return 'typing.Tuple'


@enforce
@dataclass(frozen=True)
class GenericTupleType(FakeType):
    types: tuple

    def __instancecheck__(self, instance):
        return (isinstance(instance, tuple) and
                len(self.types) == len(instance) and
                all(isinstance(x, t) for t, x in zip(self.types, instance)))

    def __repr__(self):
        return f'typing.Tuple[{", ".join(map(repr, self.types))}]'


@enforce
@dataclass(frozen=True)
class SequenceTupleType(FakeType):
    type: object

    def __instancecheck__(self, instance):
        return (isinstance(instance, tuple) and
                all(isinstance(x, self.type) for x in instance))

    def __repr__(self):
        return f'typing.Tuple[{repr(self.type)}, ...]'


@enforce
@dataclass(frozen=True)
class ListType(FakeType):

    def __getitem__(self, subtype):
        return GenericListType(subtype)

    def __instancecheck__(self, instance):
        return isinstance(instance, list)

    def __repr__(self):
        return 'typing.List'


@enforce
@dataclass(frozen=True)
class GenericListType(FakeType):
    type: object

    def __instancecheck__(self, instance):
        return (isinstance(instance, list) and
                all(isinstance(x, self.type) for x in instance))

    def __repr__(self):
        return f'typing.List[{repr(self.type)}]'


@enforce
@dataclass(frozen=True)
class OptionalType(FakeType):
    def __getitem__(self, subtype):
        return GenericOptionalType(subtype)

    def __instancecheck__(self, instance):
        return True

    def __repr__(self):
        return 'typing.Optional'


@enforce
@dataclass(frozen=True)
class GenericOptionalType(FakeType):
    type: object

    def __instancecheck__(self, instance):
        return instance is None or isinstance(instance, self.type)

    def __repr__(self):
        return f'typing.Optional[{repr(self.type)}]'


Union = UnionType()
Tuple = TupleType()
List = ListType()
Optional = OptionalType()
Pattern = typing.Pattern
Match = typing.Match
Callable = typing.Callable
Iterable = typing.Iterable
Iterator = typing.Iterator
Set = typing.Set
Dict = typing.Dict
NamedTuple = typing.NamedTuple


@test.case
def test_union():
    test.that(isinstance('hi', Union[int, str]))
    test.that(isinstance(15, Union[int, str]))
    test.that(not isinstance(15.0, Union[int, str]))


@test.case
def test_tuple():
    test.that(isinstance((), Tuple))
    test.that(isinstance((), Tuple[()]))
    test.that(isinstance((5, ), Tuple[int]))
    test.that(not isinstance((5, ), Tuple[int, int]))
    test.that(isinstance((5, 10), Tuple[int, int]))
    test.that(not isinstance((5, '10'), Tuple[int, int]))


@test.case
def test_list():
    test.that(isinstance([], List))
    test.that(isinstance([], List[int]))
    test.that(not isinstance(['hi'], List[int]))
    test.that(isinstance([51], List[int]))


@test.case
def test_optional():
    test.that(isinstance(51.1, Optional))
    test.that(isinstance(None, Optional))
    test.that(not isinstance(10, Optional[str]))
    test.that(isinstance('hi', Optional[str]))
    test.that(isinstance(None, Optional[str]))

