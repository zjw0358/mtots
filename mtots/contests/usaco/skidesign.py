"""
ID: math4to3
TASK: skidesign
LANG: PYTHON3
"""


def main(open):
    with open('skidesign.in') as f:
        lines = iter(f.read().strip().splitlines())
        N = int(next(lines))
        heights = [int(next(lines)) for _ in range(N)]

    cost = min(compute_cost(heights, i) for i in range(100))

    with open('skidesign.out', 'w') as f:
        f.write(f'{cost}\n')


def compute_cost(heights, min_height):
    max_height = min_height + 17
    cost = 0
    for height in heights:
        if height < min_height:
            cost += (min_height - height) ** 2
        elif height > max_height:
            cost += (height - max_height) ** 2
    return cost


if __name__ == '__main__':
    main(open)


def _sample():
    _t({
'skidesign.in': """5
20
4
1
24
21
"""
    }, {
'skidesign.out': """18
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
