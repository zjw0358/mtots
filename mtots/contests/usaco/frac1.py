"""
ID: math4to3
TASK: frac1
LANG: PYTHON3
"""
from fractions import Fraction


def main(open):
    with open('frac1.in') as f:
        N = int(f.read())

    fractions = sorted({
        Fraction(n, d)
        for d in range(1, N + 1)
        for n in range(d + 1)
    })

    with open('frac1.out', 'w') as f:
        for fr in fractions:
            f.write(f'{fr.numerator}/{fr.denominator}\n')


if __name__ == '__main__':
    main(open)
else:
    from mtots import test
    from . import _testutil

    @test.case
    def _sample():
        _testutil.case(main, {
'frac1.in': """5
"""
        }, {
'frac1.out': """0/1
1/5
1/4
1/3
2/5
1/2
3/5
2/3
3/4
4/5
1/1
""",
        })
