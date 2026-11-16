"""
entity.py - Smooth tile-to-tile movement shared by Pac-Man and the ghosts.

Characters live on a grid but are DRAWN smoothly between tiles:
    tile       the tile the character last arrived at
    next_tile  the tile it is walking towards (None if standing still)
    progress   0.0 .. 1.0, how far it is along that step
Whenever a character arrives on a tile, it asks a "chooser" function which
tile to walk to next. For Pac-Man the chooser is the A* AI (or the keyboard);
for ghosts it is BFS.
"""


class Mover:
    def __init__(self, start_tile):
        self.start_tile = start_tile
        self.reset()

    def reset(self):
        self.tile = self.start_tile
        self.next_tile = None
        self.prev_tile = None
        self.progress = 0.0
        self.direction = (0, 0)

    @property
    def pos(self):
        """Exact (float) position in tile units, used for drawing."""
        if self.next_tile is None:
            return (float(self.tile[0]), float(self.tile[1]))
        t = self.progress
        return (self.tile[0] + (self.next_tile[0] - self.tile[0]) * t,
                self.tile[1] + (self.next_tile[1] - self.tile[1]) * t)

    @property
    def current_tile(self):
        """The tile the character is closest to right now."""
        if self.next_tile is not None and self.progress >= 0.5:
            return self.next_tile
        return self.tile

    def reverse(self):
        """Turn around in the middle of a step."""
        if self.next_tile is None:
            return
        self.tile, self.next_tile = self.next_tile, self.tile
        self.progress = 1.0 - self.progress
        self.direction = (-self.direction[0], -self.direction[1])

    def move(self, dt, speed, choose_next):
        """
        Advance by `speed` tiles per second for `dt` seconds.
        choose_next() is called whenever the character needs a new target
        tile; it must return a neighbouring tile or None (= stand still).
        """
        remaining = speed * dt
        guard = 0
        while remaining > 1e-9 and guard < 60:
            guard += 1
            if self.next_tile is None:
                nxt = choose_next()
                if nxt is None:
                    return
                self.direction = (nxt[0] - self.tile[0], nxt[1] - self.tile[1])
                self.next_tile = nxt
                self.progress = 0.0
            need = 1.0 - self.progress
            if remaining >= need:
                remaining -= need
                self.prev_tile = self.tile
                self.tile = self.next_tile
                self.next_tile = None
                self.progress = 0.0
            else:
                self.progress += remaining
                remaining = 0.0
