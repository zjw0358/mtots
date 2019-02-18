"""
ID: math4to3
TASK: milk3
LANG: PYTHON3
"""
import itertools


def main(open):
    with open('milk3.in') as f:
        A, B, C = map(int, f.read().split())

    answer = sorted(solve(A, B, C))

    with open('milk3.out', 'w') as f:
        f.write(' '.join(map(str, answer)) + '\n')


def solve(A, B, C):
    S = [A, B, C]

    def pour(state, src, dest):
        new_state = list(state)
        amount = min(state[src], S[dest] - state[dest])
        new_state[src] -= amount
        new_state[dest] += amount
        return tuple(new_state)

    def neighbors_of(state):
        for i, j in itertools.product(range(3), range(3)):
            if i != j:
                yield pour(state, i, j)

    answer = set()
    queue = [(0, 0, C)]
    seen = set(queue)
    while queue:
        a, b, c = state = queue.pop()
        if a == 0:
            answer.add(c)
        for neighbor in neighbors_of(state):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return answer


if __name__ == '__main__':
    main(open)
else:
    from mtots import test
    from . import _testutil

    @test.case
    def _sample():
        _testutil.case(main, {
'milk3.in': """8 9 10
"""
        }, {
'milk3.out': """1 2 8 9 10
""",
        })

    @test.case
    def _sample2():
        _testutil.case(main, {
'milk3.in': """2 5 10
"""
        }, {
'milk3.out': """5 6 7 8 9 10
""",
        })
