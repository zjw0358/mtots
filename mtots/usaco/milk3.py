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


def _sample():
    _t({
'milk3.in': """8 9 10
"""
    }, {
'milk3.out': """1 2 8 9 10
""",
    })


def _sample2():
    _t({
'milk3.in': """2 5 10
"""
    }, {
'milk3.out': """5 6 7 8 9 10
""",
    })


def _t(inputs, outputs):
    from mtots import test
    import contextlib

    contents = dict(inputs)

    @contextlib.contextmanager
    def open(name, mode='r'):
        if mode == 'r':
            yield FakeFile('r', contents[name])
        elif mode == 'w':
            fake_file = FakeFile('w', '')
            yield fake_file
            contents[name] = fake_file.read()
        else:
            assert False, mode

    main(open)

    for filename in outputs:
        test.that(filename in contents, f'File {filename} missing')
        test.equal(
            f'FILE{filename}:{contents[filename]}',
            f'FILE{filename}:{outputs[filename]}',
        )


class FakeFile:
    def __init__(self, mode, data):
        assert isinstance(data, str)
        self.mode = mode
        self.contents = [data]

    def write(self, data):
        assert isinstance(data, str), repr(data)
        assert self.mode == 'w', self.mode
        self.contents.append(data)

    def read(self):
        return ''.join(self.contents)


try:
    import mtots.test
    mtots.test.case(_sample)
    mtots.test.case(_sample2)
except ImportError:
    pass
