"""
maze.py - The maze: walls, corridors, food and helper functions.

The maze is drawn as text. Each character is one tile:
    #  wall            .  small dot          o  power pellet
    -  ghost door      (space) empty corridor
    P  Pac-Man start   (a dot is NOT placed under P)
Ghost start positions are listed separately below.

A tile is a tuple (column, row). Column 0 is the left side, row 0 the top.
"""

TILE = 28  # size of one tile in pixels

LAYOUT = [
    "###################",
    "#........#........#",
    "#.##.###.#.###.##.#",
    "#o...............o#",
    "#.##.#.#####.#.##.#",
    "#....#...#...#....#",
    "####.### # ###.####",
    "####.#       #.####",
    "####.# ##-## #.####",
    "####.  #   #  .####",
    "####.# ##### #.####",
    "####.#       #.####",
    "####.# ##### #.####",
    "#........#........#",
    "#.##.###.#.###.##.#",
    "#o.#.....P.....#.o#",
    "##.#.#.#####.#.#.##",
    "#....#...#...#....#",
    "#.######.#.######.#",
    "#.................#",
    "###################",
]

# Where each ghost starts: (column, row). Blinky starts outside the house.
GHOST_STARTS = {
    "Blinky": (9, 7),
    "Pinky": (9, 9),
    "Inky": (8, 9),
    "Clyde": (10, 9),
}

DIRECTIONS = [(0, -1), (-1, 0), (0, 1), (1, 0)]  # up, left, down, right


class Maze:
    def __init__(self, layout=LAYOUT):
        self.layout = layout
        self.height = len(layout)
        self.width = len(layout[0])
        for row in layout:
            if len(row) != self.width:
                raise ValueError("Maze rows must all have the same length")

        self.walls = set()
        self.doors = set()
        self.pac_start = None
        self._initial_dots = set()
        self._initial_pellets = set()
        for r, row in enumerate(layout):
            for c, ch in enumerate(row):
                if ch == "#":
                    self.walls.add((c, r))
                elif ch == "-":
                    self.doors.add((c, r))
                elif ch == ".":
                    self._initial_dots.add((c, r))
                elif ch == "o":
                    self._initial_pellets.add((c, r))
                elif ch == "P":
                    self.pac_start = (c, r)
        if self.pac_start is None:
            raise ValueError("Maze has no Pac-Man start 'P'")

        self.ghost_starts = dict(GHOST_STARTS)
        self.house_exit = (9, 7)  # the tile just above the ghost door

        # Pre-compute the neighbours of every walkable tile (faster AI).
        # Pac-Man cannot pass the ghost door; ghosts can.
        self._nbrs = {False: {}, True: {}}
        for r in range(self.height):
            for c in range(self.width):
                t = (c, r)
                if t in self.walls:
                    continue
                for ghost in (False, True):
                    if t in self.doors and not ghost:
                        continue
                    self._nbrs[ghost][t] = [
                        (c + dx, r + dy)
                        for dx, dy in DIRECTIONS
                        if self.is_walkable((c + dx, r + dy), ghost)
                    ]
        self.walkable_tiles = list(self._nbrs[True].keys())
        self.reset_food()

    # ------------------------------------------------------------------
    def reset_food(self):
        """Put all dots and power pellets back (start of a new game)."""
        self.dots = set(self._initial_dots)
        self.pellets = set(self._initial_pellets)
        self.total_food = len(self.dots) + len(self.pellets)

    def in_bounds(self, tile):
        return 0 <= tile[0] < self.width and 0 <= tile[1] < self.height

    def is_wall(self, tile):
        return (not self.in_bounds(tile)) or tile in self.walls

    def is_walkable(self, tile, ghost=False):
        """Can this tile be entered? Only ghosts may use the door."""
        if self.is_wall(tile):
            return False
        if tile in self.doors and not ghost:
            return False
        return True

    def neighbors(self, tile, ghost=False):
        """Walkable tiles next to `tile` (up, left, down, right)."""
        return self._nbrs[ghost].get(tile, [])

    def nearest_walkable(self, tile):
        """The walkable tile closest to `tile` (used for ghost targets)."""
        return min(self.walkable_tiles,
                   key=lambda t: abs(t[0] - tile[0]) + abs(t[1] - tile[1]))

    @property
    def food_left(self):
        return len(self.dots) + len(self.pellets)
