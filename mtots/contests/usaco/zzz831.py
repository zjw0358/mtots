"""
USACO 2018 US Open Contest, Bronze
Problem 1. Team Tic Tac Toe
"""


def main(open):
    with open('tttt.in') as f:
        rows = [row.strip() for row in f.read().strip().splitlines()]

    assert len(rows) == 3, rows
    for r in range(3):
        assert len(rows[r]) == 3, (r, rows[r])

    winning_teams = {
        # win by row
        frozenset(row) for row in rows
    } | {
        # win by column
        frozenset(rows[r][c] for r in range(3)) for c in range(3)
    } | {
        # win by diagonal
        frozenset({rows[r][r] for r in range(3)}),
        frozenset({rows[r][2 - r] for r in range(3)}),
    }

    with open('tttt.out', 'w') as f:
        winner_maps = {
            size: len({team for team in winning_teams if len(team) == size})
            for size in (1, 2)
        }
        f.write('%s\n' % winner_maps[1])
        f.write('%s\n' % winner_maps[2])


if __name__ == '__main__':
    main(open)
else:
    from mtots import test
    from . import _testutil

    @test.case
    def _sample():
        _testutil.case(main, {
'tttt.in': """COW
XXO
ABC
"""
        }, {
'tttt.out': """0
2
""",
        })

    @test.case
    def _all_same():
        _testutil.case(main, {
'tttt.in': """XXX
XXX
XXX
"""
        }, {
'tttt.out': """1
0
""",
        })

    @test.case
    def _all_different():
        _testutil.case(main, {
'tttt.in': """ABC
DEF
GHI
"""
        }, {
'tttt.out': """0
0
""",
        })
