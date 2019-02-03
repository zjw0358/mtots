"""
ID: math4to3
TASK: milk
LANG: PYTHON3
"""


def main(open):
    with open('milk.in') as f:
        lines = iter(f.read().strip().splitlines())
        N, M = map(int, next(lines).split())
        suppliers = [tuple(map(int, next(lines).split())) for _ in range(M)]

    suppliers.sort(reverse=True)
    cost = 0
    while N > 0:
        P, A = suppliers.pop()
        A = min(A, N)
        N -= A
        cost += P * A

    with open('milk.out', 'w') as f:
        f.write(f'{cost}\n')


if __name__ == '__main__':
    main(open)


def _sample():
    _t({
'milk.in': """100 5
5 20
9 40
3 10
8 80
6 30
"""
    }, {
'milk.out': """630
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
