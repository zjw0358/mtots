"""
ID: math4to3
TASK: crypt1
LANG: PYTHON3
"""
import itertools


def main(open):
    with open('crypt1.in') as f:
        digit_set = set(map(int, f.read().splitlines()[1].split()))

    total = 0
    for a_digits in itertools.product(digit_set, repeat=3):
        a = from_digits(a_digits)
        for b_digits in itertools.product(digit_set, repeat=2):
            b = from_digits(b_digits)
            if check_pair(digit_set, a, b):
                total += 1

    with open('crypt1.out', 'w') as f:
        f.write(f'{total}\n')


def from_digits(digits):
    ret = 0
    for digit in digits:
        ret *= 10
        ret += digit
    return ret


def check_pair(digit_set, a, b):
    return (
        check_number(digit_set, a, 3) and
        check_number(digit_set, b, 2) and
        check_number(digit_set, a * (b % 10), 3) and
        check_number(digit_set, a * (b // 10), 3) and
        check_number(digit_set, a * b, 4)
    )


def check_number(digit_set, x, n):
    digits = []
    while x:
        digits.append(x % 10)
        x //= 10
    return len(digits) == n and all(digit in digit_set for digit in digits)


if __name__ == '__main__':
    main(open)


def _sample():
    _t({
'crypt1.in': """5
2 3 4 6 8
"""
    }, {
'crypt1.out': """1
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
