"""
ID: math4to3
TASK: ariprog
LANG: PYTHON3
"""
"""
Conceptually simple, but it seems to be incredibly difficult
to get a Python program fast enough to pass.
So instead, see ariprog.cc for a C++ version that can actually
pass without a time limit exceeded.
"""
import itertools
import gc
gc.disable()


def main(open):
    with open('ariprog.in') as f:
        lines = iter(f.read().strip().splitlines())
        N = int(next(lines))
        M = int(next(lines))

    seqs = tuple(solve(N, M))

    with open('ariprog.out', 'w') as f:
        if seqs:
            for i, diff in seqs:
                f.write(f'{i} {diff}\n')
        else:
            f.write(f'NONE\n')


def solve(N, M):
    "bisquare set"
    bss = [False] * (M ** 2 * 2 + 1)
    for p in range(M + 1):
        for q in range(p, M + 1):
            bss[p ** 2 + q ** 2] = True

    "bisquare list"
    bsl = [i for i in range(len(bss)) if bss[i]]

    B = len(bsl)

    for diff in range(1, bsl[-1] // 2 + 1):
        for bsi in bsl:
            for i in range(N):
                val = bsi + diff * i
                if val >= len(bss) or not bss[val]:
                    break
            else:
                yield bsi, diff


if __name__ == '__main__':
    main(open)


def _sample():
    _t({
'ariprog.in': """5
7
"""
    }, {
'ariprog.out': """1 4
37 4
2 8
29 8
1 12
5 12
13 12
17 12
5 20
2 24
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
except ImportError:
    pass
