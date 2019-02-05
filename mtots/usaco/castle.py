"""
ID: math4to3
TASK: castle
LANG: PYTHON3
"""


def main(open):
    with open('castle.in') as f:
        lines = f.read().strip().splitlines()
        M, N = map(int, lines[0].split())
        walls_gen = iter(
            int(word) for line in lines[1:] for word in line.split()
        )
        walls = [[None for _ in range(M)] for _ in range(N)]
        for r in range(N):
            for c in range(M):
                walls[r][c] = next(walls_gen)

    R, max_room_size, combined_room_size, removed_wall_name = (
        solve(M, N, walls)
    )

    with open('castle.out', 'w') as f:
        f.write(f'{R}\n')
        f.write(f'{max_room_size}\n')
        f.write(f'{combined_room_size}\n')
        f.write(f'{removed_wall_name}\n')


def solve(M, N, walls):
    assert len(walls) == N, [len(walls), N]
    assert len(walls[0]) == M, [len(walls[0]), M]

    WEST = 1
    NORTH = 2
    EAST = 4
    SOUTH = 8
    DIRS = (NORTH, SOUTH, EAST, WEST)

    def dir_id(dir):
        if dir == EAST:
            return 'E'
        elif dir == NORTH:
            return 'N'
        assert False, dir

    def _move(r, c, dir):
        if dir == NORTH:
            return r - 1, c
        elif dir == SOUTH:
            return r + 1, c
        elif dir == EAST:
            return r, c + 1
        elif dir == WEST:
            return r, c - 1
        assert False, dir

    def move(r, c, dir):
        r, c = _move(r, c, dir)
        return (r, c) if r in range(N) and c in range(M) else None

    R = 0
    room = [[None for _ in range(M)] for _ in range(N)]
    room_size = []

    def fill(r, c, R):
        assert len(room_size) == R, [len(room_size), R]
        room_size.append(1)
        room[r][c] = R
        queue = [(r, c)]
        while queue:
            r, c = queue.pop()
            for dir in DIRS:
                if not (walls[r][c] & dir):
                    nr, nc = move(r, c, dir)
                    if room[nr][nc] is None:
                        room[nr][nc] = R
                        room_size[-1] += 1
                        queue.append((nr, nc))

    for r in range(N):
        for c in range(M):
            if room[r][c] is None:
                fill(r, c, R)
                R += 1

    # Find which wall to tear down
    combined_room_size = 0
    for c in range(M):
        for r in reversed(range(N)):
            for dir in (NORTH, EAST):
                # If there's no wall, there's nothing to do
                if not (walls[r][c] & dir):
                    continue

                # If we've walked off the edge, there's nothing to do
                neighb = move(r, c, dir)
                if neighb is None:
                    continue

                # If both sides of the wall are the same room,
                # there's nothing to do
                nr, nc = neighb
                if room[r][c] == room[nr][nc]:
                    continue

                new_room_size = (
                    room_size[room[r][c]] +
                    room_size[room[nr][nc]]
                )
                if new_room_size > combined_room_size:
                    combined_room_size = new_room_size
                    removed_wall_name = f'{r + 1} {c + 1} {dir_id(dir)}'

    return (
        R,
        max(room_size),
        combined_room_size,
        removed_wall_name,
    )


if __name__ == '__main__':
    main(open)
else:
    from mtots import test
    from . import _testutil

    @test.case
    def _sample():
        _testutil.case(main, {
'castle.in': """7 4
11 6 11 6 3 10 6
7 9 6 13 5 15 5
1 10 12 7 13 7 5
13 11 10 8 10 12 13
"""
        }, {
'castle.out': """5
9
16
4 1 E
""",
        })
