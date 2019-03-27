"""
USACO 2018 US Open Contest, Silver
Problem 1. Out of Sorts
"""


def main(open):
    with open('sort.in') as f:
        lines = iter(f)
        N = int(next(lines))
        A = [int(next(lines)) for _ in range(N)]

    AI = [(a, i) for i, a in enumerate(A)]
    SAI = sorted(AI)
    answer = max(i - j for j, (a, i) in enumerate(SAI)) + 1

    with open('sort.out', 'w') as f:
        f.write('%s\n' % answer)


if __name__ == '__main__':
    main(open)
else:
    from mtots import test
    from . import _testutil

    @test.case
    def _sample():
        _testutil.case(main, {
'sort.in': """5
1
5
3
8
2
"""
        }, {
'sort.out': """4
""",
        })
