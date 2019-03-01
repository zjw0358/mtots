from mtots import test
import itertools


class Multimethod:

    class Builder:
        def __init__(self, name, n):
            self.name = name
            self.n = n
            self.table = {}

        def on(self, *types):
            if len(types) != self.n:
                raise TypeError(
                    f'Multimethod {repr(self.name)}: '
                    f'n = {self.n}, but provided types = {types}'
                )
            def wrapper(f):
                self.table[types] = f
                return self
            return wrapper

        def __call__(self, *args):
            return self.on(*args)

    @staticmethod
    def new(n):
        def wrapper(f):
            name = f.__name__
            builder = Multimethod.Builder(name=name, n=n)
            f(builder)
            return Multimethod(name=name, n=n, table=builder.table)
        return wrapper

    def __init__(self, name, n, table):
        # n = number of arguments whose types
        # we take into account for dispatch
        self.name = name
        self.n = n
        self._table = table

    def __repr__(self):
        return f'Multimethod({self.name}, {self.n})'

    def find(self, types):
        "Find and return the implementation for the given arg types"
        if types not in self._table:
            mrolist = [t.__mro__ for t in types]
            for basetypes in itertools.product(*mrolist):
                if basetypes in self._table:
                    self._table[types] = self._table[basetypes]
                    break
            else:
                raise TypeError(
                    f'{repr(self.name)} is not defined for types {types}')
        return self._table[types]

    def __call__(self, *args, **kwargs):
        types = tuple(type(arg) for arg in args[:self.n])
        f = self.find(types)
        return f(*args, **kwargs)


multimethod = Multimethod.new


@test.case
def test_multimethod():

    @multimethod(2)
    def foo(builder):
        @builder.on(int, int)
        def foo(a, b):
            return 'int'

        @builder.on(str, str)
        def foo(a, b):
            return 'str'

        @builder.on(object, float)
        def foo(a, b):
            return 'object/float'

    test.equal(foo(1, 1), 'int')
    test.equal(foo('a', 'b'), 'str')
    test.equal(foo('asdf', 1.1), 'object/float')

    @test.throws(TypeError)
    def invalid_types():
        foo('a', 4)
