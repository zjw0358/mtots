from mtots import test

try:
    from dataclasses import dataclass
    from dataclasses import field
except ImportError:
    # If we're not on Python 3.7+, see
    # if we can use the 3.6 backport
    from mtots.tp.dataclasses.main import dataclass
    from mtots.tp.dataclasses.main import field


@test.case
def test_inheritance():

    @dataclass
    class A:
        a : int

    @dataclass
    class B(A):
        b : str

    b = B(10, 'a')
    test.equal(b.a, 10)
    test.equal(b.b, 'a')

    a = A(76)
    test.equal(a.a, 76)
    test.that(not hasattr(a, 'b'))
