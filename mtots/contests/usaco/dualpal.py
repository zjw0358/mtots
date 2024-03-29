"""
ID: math4to3
TASK: dualpal
LANG: PYTHON3
"""


def main(open):
    with open('dualpal.in') as f:
        N, S = map(int, f.read().split())

    numbers = []

    while N > 0:
        S += 1
        while True:
            if is_dualpal(S):
                numbers.append(S)
                break
            S += 1
        N -= 1

    with open('dualpal.out', 'w') as f:
        for number in numbers:
            f.write(f'{number}\n')

def is_dualpal(n):
    return sum(is_pal(n, base) for base in range(2, 11)) >= 2


def is_pal(n, base):
    digits = []
    while n:
        digits.append(n % base)
        n //= base

    return digits == list(reversed(digits))


if __name__ == '__main__':
    main(open)


def _sample():
    _t(
        inputs={
'dualpal.in':
"""3 25
""",
        },
        outputs={
'dualpal.out':
"""26
27
28
""",
        },
    )


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
