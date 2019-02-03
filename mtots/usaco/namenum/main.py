"""
ID: math4to3
LANG: PYTHON3
TASK: namenum
"""
def main():
    with open('namenum.in') as f:
        numstr = f.read().strip()

    with open('dict.txt') as f:
        names = tuple(line.strip() for line in f.read().strip().splitlines())

    matching_names = tuple(find_matching_names(numstr, names))

    with open('namenum.out', 'w') as f:
        if matching_names:
            for name in matching_names:
                f.write(f'{name}\n')
        else:
            f.write('NONE\n')


def find_matching_names(numstr, names):
    for name in names:
        if matches(numstr, name):
            yield name


def matches(numstr, name):
    return (
        len(numstr) == len(name) and
        all(matches_char(digit, ch) for digit, ch in zip(numstr, name))
    )


def matches_char(digit, ch):
    return ch in {
        '1': set(),
        '2': {'A', 'B', 'C'},
        '3': {'D', 'E', 'F'},
        '4': {'G', 'H', 'I'},
        '5': {'J', 'K', 'L'},
        '6': {'M', 'N', 'O'},
        '7': {'P', 'R', 'S'},
        '8': {'T', 'U', 'V'},
        '9': {'W', 'X', 'Y'},
    }[digit]


if __name__ == '__main__':
    main()
