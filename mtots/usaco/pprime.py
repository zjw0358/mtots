"""
ID: math4to3
TASK: pprime
LANG: PYTHON3
"""


def main(open):
    with open('pprime.in') as f:
        a, b = map(int, f.read().split())

    with open('pprime.out', 'w') as f:
        for x in solve(a, b):
            f.write(f'{x}\n')


def solve(a, b):

    def generate_palindromes():
        D = len(str(b))

        for i in range(10):
            yield i

        for i in range(10 ** (D // 2)):
            istr = str(i)
            value = int(istr + istr[::-1])
            if value > b:
                break
            yield value

        for i in range(10 ** ((D - 1) // 2)):
            istr = str(i)
            rstr = istr[::-1]
            for middle in range(10):
                value = int(istr + str(middle) + rstr)
                if value > b:
                    return
                yield value

    def is_prime(x):
        for p in range(2, int(x ** 0.5) + 1):
            if x % p == 0:
                return False
        return True

    return sorted(
        x for x in generate_palindromes() if x >= a and is_prime(x)
    )


if __name__ == '__main__':
    main(open)
else:
    from mtots import test
    from . import _testutil

    @test.case
    def _sample():
        _testutil.case(main, {
'pprime.in': """5 500
"""
        }, {
'pprime.out': """5
7
11
101
131
151
181
191
313
353
373
383
""",
        })

    @test.case
    def _sample2():
        _testutil.case(main, {
'pprime.in': """99999999 100000000
"""
        }, {
'pprime.out': '',
        })
