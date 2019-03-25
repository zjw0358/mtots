"""
USACO 2018 US Open Contest, Bronze
Problem 2. Milking Order
"""


def main(open):
    with open('milkorder.in') as f:
        lines = iter(f)
        N, M, K = map(int, next(lines).split())
        m = list(map(int, next(lines).split()))
        r = {}
        for _ in range(K):
            c, p = map(int, next(lines).split())
            r[c] = p

    if 1 in r:
        # Case 1: position of cow 1 is fixed
        answer = r[1]
    elif 1 in m:
        # Case 2: Cow 1 is in the social hierarchy
        # We want to push up the hierachy as early as possible
        positions = sorted(
            {p for p in range(1, N + 1)} - set(r.values()),
            reverse=True,
        )
        for mi in m:
            if mi in r:
                while positions and positions[-1] <= r[mi]:
                    positions.pop()
            else:
                r[mi] = positions.pop()
        answer = r[1]
    else:
        # Case 3: Cow 1 is not in the social hierachy
        # We want to push back the hierachy as late as possible,
        # then cow 1 can be placed in the earliest remaining position.
        positions = sorted(
            {p for p in range(1, N + 1)} - set(r.values())
        )
        for mi in reversed(m):
            if mi in r:
                while positions and positions[-1] >= r[mi]:
                    positions.pop()
            else:
                r[mi] = positions.pop()
        answer = min(set(range(1, N + 1)) - set(r.values()))

    with open('milkorder.out', 'w') as f:
        f.write('%s\n' % answer)


if __name__ == '__main__':
    main(open)
else:
    from mtots import test
    from . import _testutil

    @test.case
    def _sample():
        _testutil.case(main, {
'milkorder.in': """6 3 2
4 5 6
5 3
3 1
"""
        }, {
'milkorder.out': """4
""",
        })
