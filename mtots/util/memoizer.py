from mtots import test
import functools


def memoize(f):

    memo = {}

    @functools.wraps(f)
    def g(*args):
        if args not in memo:
            memo[args] = f(*args)
        return memo[args]

    return g



@test.case
def test_memoized_fibonacci():

    @memoize
    def fib(i):
        if i <= 1:
            return 1
        else:
            return fib(i - 1) + fib(i - 2)

    test.equal(fib(0), 1)
    test.equal(fib(1), 1)
    test.equal(fib(2), 2)
    test.equal(fib(3), 3)
    test.equal(fib(4), 5)
    test.equal(fib(5), 8)
    test.equal(fib(6), 13)
    test.equal(fib(60), 2504730781961)

