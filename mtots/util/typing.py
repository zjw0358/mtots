from .dataclasses import dataclass
import functools
import typing


def check(cls):

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


@check
@dataclass(frozen=True)
class UnionType(FakeType):

    def __getitem__(self, *types):
        return GenericUnionType(types)

    def __instancecheck__(self, instance):
        return True

    def __repr__(self):
        return 'typing.Union'


@check
@dataclass(frozen=True)
class GenericUnionType(FakeType):
    types: tuple

    def __instancecheck__(self, instance):
        return any(isinstance(instance, t) for t in self.types)

    def __repr__(self):
        return f'typing.Union[{", ".join(map(repr, self.types))}]'


@check
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


@check
@dataclass(frozen=True)
class GenericTupleType(FakeType):
    types: tuple

    def __instancecheck__(self, instance):
        return (isinstance(instance, tuple) and
                len(self.types) == len(instance) and
                all(isinstance(x, t) for t, x in zip(self.types, instance)))

    def __repr__(self):
        return f'typing.Tuple[{", ".join(map(repr, self.types))}]'


@check
@dataclass(frozen=True)
class SequenceTupleType(FakeType):
    type: object

    def __instancecheck__(self, instance):
        return (isinstance(instance, tuple) and
                all(isinstance(x, self.type) for x in instance))

    def __repr__(self):
        return f'typing.Tuple[{repr(self.type)}, ...]'


@check
@dataclass(frozen=True)
class ListType(FakeType):

    def __getitem__(self, subtype):
        return GenericListType(subtype)

    def __instancecheck__(self, instance):
        return isinstance(instance, list)

    def __repr__(self):
        return 'typing.List'


@check
@dataclass(frozen=True)
class GenericListType(FakeType):
    type: object

    def __instancecheck__(self, instance):
        return (isinstance(instance, list) and
                all(isinstance(x, self.type) for x in instance))

    def __repr__(self):
        return f'typing.List[{repr(self.type)}]'


@check
@dataclass(frozen=True)
class OptionalType(FakeType):
    def __getitem__(self, subtype):
        return GenericOptionalType(subtype)

    def __instancecheck__(self, instance):
        return True

    def __repr__(self):
        return 'typing.Optional'


@check
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
