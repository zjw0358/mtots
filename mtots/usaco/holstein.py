"""
ID: math4to3
TASK: holstein
LANG: PYTHON3
"""


def main(open):
    with open('holstein.in') as f:
        lines = iter(f)
        V = int(next(lines))
        req = list(map(int, next(lines).split()))
        G = int(next(lines))
        feed = [tuple(map(int, next(lines).split())) for _ in range(G)]

    best = None

    for i in range(2 ** G):
        feed_types = []
        feed_type = 1
        vits = [0] * V
        for feed_type in range(1, G + 1):
            if (i >> (feed_type - 1)) % 2:
                feed_types.append(feed_type)
                for j, vit in enumerate(feed[feed_type - 1]):
                    vits[j] += vit

        if all(v >= r for v, r in zip(vits, req)):
            if best is None:
                best = feed_types

            if (len(feed_types) < len(best) or
                    (len(feed_types) == len(best) and feed_types < best)):
                best = feed_types

    with open('holstein.out', 'w') as f:
        f.write(f'{len(best)} {" ".join(map(str, best))}\n')


if __name__ == '__main__':
    main(open)
else:
    from mtots import test
    from . import _testutil

    @test.case
    def _sample():
        _testutil.case(main, {
'holstein.in': """4
100 200 300 400
3
50   50  50  50
200 300 200 300
900 150 389 399
"""
        }, {
'holstein.out': """2 1 3
""",
        })
