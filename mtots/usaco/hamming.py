"""
ID: math4to3
TASK: hamming
LANG: PYTHON3
"""
import itertools


def main(open):
    with open('hamming.in') as f:
        N, B, D = map(int, f.read().split())

    codewords = solve(N, B, D)

    with open('hamming.out', 'w') as f:
        if codewords:
            for i in range(len(codewords)):
                f.write(f'{codewords[i]}')
                if i % 10 == 9 or i == len(codewords) - 1:
                    f.write('\n')
                else:
                    f.write(' ')
        else:
            f.write(f'NO SOLUTION\n')


def solve(N, B, D):
    INF = 2 ** B * 2

    def dist(a, b):
        return sum((a >> i) % 2 ^ (b >> i) % 2 for i in range(B))

    neighbors_of = {}
    for a in range(2 ** B):
        neighbors_of[a] = set()
        for b in range(2 ** B):
            if dist(a, b) < D:
                neighbors_of[a].add(b)

    known_impossible = {(): 1}

    def recurse(codewords, remaining):
        needed = N - len(codewords)

        if needed <= 0:
            return codewords

        if known_impossible.get(remaining, len(remaining) + 1) <= needed:
            return

        # print(f'codewords = {codewords}, remaining = {remaining}')

        if needed <= len(remaining):
            for i, val in enumerate(remaining):
                neighbors = neighbors_of[val]
                # print(f'val = {val}, neighbors = {neighbors}')
                new_remaining = tuple(
                    r
                    for r in remaining[i + 1:]
                    if r not in neighbors
                )
                codewords.append(val)
                result = recurse(codewords, new_remaining)
                if result:
                    return result
                codewords.pop()

        known_impossible[remaining] = min(
            known_impossible.get(remaining, INF),
            needed,
        )

    return recurse([], tuple(range(2 ** B)))


if __name__ == '__main__':
    main(open)
else:
    from mtots import test
    from . import _testutil

    @test.case
    def _sample():
        _testutil.case(main, {
'hamming.in': """16 7 3
"""
        }, {
'hamming.out': """0 7 25 30 42 45 51 52 75 76
82 85 97 102 120 127
""",
        })

    @test.case
    def _perf_test_1():
        _testutil.case(main, {
'hamming.in': """64 8 1
"""
        }, {
'hamming.out': """0 1 2 3 4 5 6 7 8 9
10 11 12 13 14 15 16 17 18 19
20 21 22 23 24 25 26 27 28 29
30 31 32 33 34 35 36 37 38 39
40 41 42 43 44 45 46 47 48 49
50 51 52 53 54 55 56 57 58 59
60 61 62 63
""",
        })

    @test.case
    def _perf_test_2():
        _testutil.case(main, {
'hamming.in': """64 8 7
"""
        }, {
'hamming.out': """NO SOLUTION
""",})

    @test.case
    def _perf_test_3():
        # If this was actually required, this would be
        # too slow (seems to go a bit over 2 seconds on my machine).
        # However, at least for this problem, NO SOLUTION
        # cases don't seem to count as valid input cases.
        _testutil.case(main, {
'hamming.in': """64 8 4
"""
        }, {
'hamming.out': """NO SOLUTION
""",})
