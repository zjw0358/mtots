"""
ID: math4to3
TASK: wormhole
LANG: PYTHON3
"""
import itertools


def main(open):
    with open('wormhole.in') as f:
        lines = iter(f.read().strip().splitlines())
        N = int(next(lines))
        coordinates = []
        for _ in range(N):
            coordinates.append(tuple(map(int, next(lines).split())))

    total = 0
    physical_mapping = compute_physical_mapping(coordinates)
    for wormhole_mapping in enumerate_all_wormhole_mappings(N):
        if check_pairings(N, physical_mapping, wormhole_mapping):
            total += 1

    with open('wormhole.out', 'w') as f:
        f.write(f'{total}\n')


def check_pairings(N, physical_mapping, wormhole_mapping):
    mappings = [physical_mapping, wormhole_mapping]
    cache = dict()

    def escapes(state, stack=None):
        if state not in cache:
            i, bit = state
            stack = set() if stack is None else stack
            mapping = mappings[bit]
            if state in stack:
                cache[state] = False
            elif mapping[i] is None:
                cache[state] = True
            else:
                stack.add(state)
                cache[state] = escapes((mapping[i], 1 - bit), stack)
                stack.remove(state)
        return cache[state]

    return any(not escapes((i, bit)) for i in range(N) for bit in range(2))


def compute_physical_mapping(coordinates):
    mapping = {}

    for i in range(len(coordinates)):
        mapped = None
        xi, yi = coordinates[i]
        for j, (xj, yj) in enumerate(coordinates):
            if i == j:
                continue
            xm = None if mapped is None else coordinates[mapped][0]
            if yi == yj and xi < xj and (xm is None or xj < xm):
                mapped = j
        mapping[i] = mapped

    return mapping


def enumerate_all_wormhole_mappings(N):
    I = compute_pairings_count(N)
    for i in range(I):
        remaining = 2 ** N - 1
        mapping = {}
        modulo = N - 1
        while remaining:
            a, b = find_next_pair(N, remaining, i % modulo)
            mapping[a] = b
            mapping[b] = a
            remaining ^= 1 << a
            remaining ^= 1 << b
            i //= modulo
            modulo -= 2
        yield mapping


def find_next_pair(N, remaining, choice):
    a = find_next_live_bit(remaining, 0)
    b = find_next_live_bit(remaining, a + 1)
    for _ in range(choice):
        b = find_next_live_bit(remaining, b + 1)
    return a, b


def find_next_live_bit(remaining, i):
    while not (remaining & (1 << i)):
        i += 1
    return i


def compute_pairings_count(N):
    assert N % 2 == 0, N
    c = 1
    while N > 2:
        c *= N - 1
        N -= 2
    return c


if __name__ == '__main__':
    main(open)


def _sample():
    _t({
'wormhole.in': """4
0 0
1 0
1 1
0 1
"""
    }, {
'wormhole.out': """2
""",
    })

def _another_test():
    _t({
'wormhole.in': """12
1 1
2 2
3 3
4 4
5 5
6 6
7 7
8 8
9 9
10 10
11 12
12 12
"""
    }, {
'wormhole.out': """945
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
    mtots.test.slow(_another_test)
except ImportError:
    pass
