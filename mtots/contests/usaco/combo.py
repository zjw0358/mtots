"""
ID: math4to3
TASK: combo
LANG: PYTHON3
"""
import itertools


def main(open):
    with open('combo.in') as f:
        lines = iter(f.read().splitlines())
        N = int(next(lines))
        c1 = tuple(map(int, next(lines).split()))
        c2 = tuple(map(int, next(lines).split()))

    answer = len(nearby_combos(N, c1) | nearby_combos(N, c2))

    with open('combo.out', 'w') as f:
        f.write(f'{answer}\n')


def nearby_combos(N, combo):
    a, b, c = combo
    return set(itertools.product(
        set(mod_range_inclusive(N, a - 2, a + 2)),
        set(mod_range_inclusive(N, b - 2, b + 2)),
        set(mod_range_inclusive(N, c - 2, c + 2)),
    ))


def mod_range_inclusive(N, start, end):
    i = start
    while i != end:
        yield normalize(N, i)
        i += 1
    yield normalize(N, end)


def normalize(N, i):
    result = N if i % N == 0 else i % N
    return result


if __name__ == '__main__':
    main(open)


def _sample():
    _t({
'combo.in': """50
1 2 3
5 6 7
"""
    }, {
'combo.out': """249
""",
    })


def _test2():
    _t({
'combo.in': """4
1 2 3
2 3 4
"""
    }, {
'combo.out': """64
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
    mtots.test.case(_test2)
except ImportError:
    pass
