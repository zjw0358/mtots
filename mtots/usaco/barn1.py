"""
ID: math4to3
TASK: barn1
LANG: PYTHON3
"""


def main(open):
    with open('barn1.in') as f:
        lines = iter(f.read().strip().splitlines())
        M, S, C = map(int, next(lines).split())
        cows = [int(next(lines)) for _ in range(C)]

    cows.sort()
    gaps = []
    for a, b in zip(cows, cows[1:]):
        gap = b - a - 1
        if gap:
            gaps.append(gap)

    total = max(cows) - min(cows) + 1
    gaps.sort()

    while M > 1 and gaps:
        gap = gaps.pop()
        total -= gap
        M -= 1

    with open('barn1.out', 'w') as f:
        f.write(f'{total}\n')


if __name__ == '__main__':
    main(open)


def _sample():
    _t({
'barn1.in': """4 50 18
3
4
6
8
14
15
16
17
21
25
26
27
30
31
40
41
42
43
"""
    }, {
'barn1.out': """25
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
