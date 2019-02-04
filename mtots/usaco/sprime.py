"""
ID: math4to3
TASK: sprime
LANG: PYTHON3
"""


def main(open):
    with open('sprime.in') as f:
        N = int(f.read())

    with open('sprime.out', 'w') as f:
        for sprime in solve(N):
            f.write(f'{sprime}\n')


def solve(N):

    def recurse(N):
        if N == 1:
            return (2, 3, 5, 7)
        else:
            return (
                n * 10 + digit
                    for n in recurse(N - 1)
                    for digit in (1, 3, 7, 9)
                    if is_prime(n * 10 + digit)
            )

    def is_prime(n):
        for p in range(2, int(n ** 0.5) + 1):
            if n % p == 0:
                return False
        return True

    return recurse(N)


if __name__ == '__main__':
    main(open)
else:
    from mtots import test
    from . import _testutil

    @test.case
    def _sample():
        _testutil.case(main, {
'sprime.in': """4
"""
        }, {
'sprime.out': """2333
2339
2393
2399
2939
3119
3137
3733
3739
3793
3797
5939
7193
7331
7333
7393
""",
        })
