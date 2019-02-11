"""
ID: math4to3
TASK: sort3
LANG: PYTHON3
"""
import itertools


def main(open):
    with open('sort3.in') as f:
        lines = iter(f)
        N = int(next(lines))
        nums = [int(next(lines)) for _ in range(N)]

    with open('sort3.out', 'w') as f:
        f.write(f'{solve(nums)}\n')


def solve(nums):
    N = {i: nums.count(i) for i in range(1, 4)}

    M = {(i, j): 0 for i in range(1, 4) for j in range(1, 4)}
    for i in range(1, 4):
        start = sum(N[k] for k in range(1, 4) if k < i)
        end = start + N[i]
        for k in range(start, end):
            j = nums[k]
            if i != j:
                M[i, j] += 1

    ret = 0

    for i, j in itertools.combinations(range(1, 4), 2):
        n = min(M[i, j], M[j, i])
        M[i, j] -= n
        M[j, i] -= n
        ret += n

    for i, j, k in itertools.permutations(range(1, 4), 3):
        n = min(M[i, j], M[j, k], M[k, i])
        M[i, j] -= n
        M[j, k] -= n
        M[k, i] -= n
        ret += 2 * n

    assert all(v == 0 for v in M.values()), M

    return ret


if __name__ == '__main__':
    main(open)
else:
    from mtots import test
    from . import _testutil

    @test.case
    def _sample():
        _testutil.case(main, {
'sort3.in': """9
2
2
1
3
3
3
2
3
1
"""
        }, {
'sort3.out': """4
""",
        })
