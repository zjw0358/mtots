"""
ID: math4to3
TASK: numtri
LANG: PYTHON3
"""


def main(open):
    with open('numtri.in') as f:
        lines = iter(f)
        R = int(next(lines))
        cum = tuple(map(int, next(lines).split()))
        for _ in range(R - 1):
            row = tuple(map(int, next(lines).split()))
            new_cum = tuple(
                max(
                    0 if i == 0 else x + cum[i - 1],
                    0 if i >= len(cum) else x + cum[i],
                )
                for i, x in enumerate(row)
            )
            cum = new_cum

    answer = max(cum)

    with open('numtri.out', 'w') as f:
        f.write(f'{answer}\n')


if __name__ == '__main__':
    main(open)
else:
    from mtots import test
    from . import _testutil

    @test.case
    def _sample():
        _testutil.case(main, {
'numtri.in': """5
7
3 8
8 1 0
2 7 4 4
4 5 2 6 5
"""
        }, {
'numtri.out': """30
""",
        })
