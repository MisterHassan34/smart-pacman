"""
ghost.py - The four ghosts. Every ghost uses BFS to find its way.

A ghost is always in one of four states:
    WAITING     inside the ghost house, waiting to be released
    CHASE       hunting Pac-Man (dangerous!)
    FRIGHTENED  Pac-Man ate a power pellet: slow, blue, can be eaten
    EATEN       only the eyes remain; BFS leads them back to the house

Different behaviours (what each ghost aims at while chasing):
    Blinky  aims at Pac-Man's tile directly.
    Pinky   aims 4 tiles AHEAD of Pac-Man (tries to ambush).
    Inky    aims at a point mirrored around Pac-Man relative to Blinky.
    Clyde   chases when far away, but retreats to his corner when close.
"""

import random
from algorithms import bfs, manhattan
from entity import Mover

WAITING, CHASE, FRIGHTENED, EATEN = "WAITING", "CHASE", "FRIGHTENED", "EATEN"

GHOST_SPEED = 4.7
FRIGHTENED_SPEED = 3.0
EATEN_SPEED = 9.0

BEHAVIOR_TEXT = {
    "Blinky": "BFS to Pac-Man",
    "Pinky": "BFS to 4 tiles ahead",
    "Inky": "BFS to mirrored point",
    "Clyde": "BFS (shy when near)",
}


class Ghost(Mover):
    def __init__(self, name, start_tile, color, release_time, rng=None):
        self.name = name
        self.color = color
        self.release_time = release_time
        self.rng = rng or random.Random()
        self.corner = (1, 19)            # Clyde's hiding corner
        super().__init__(start_tile)

    def reset(self):
        super().reset()
        self.state = CHASE if self.release_time <= 0 else WAITING
        self.timer = self.release_time
        self.path = []                   # last BFS path (for the visualisation)

    @property
    def speed(self):
        if self.state == FRIGHTENED:
            return FRIGHTENED_SPEED
        if self.state == EATEN:
            return EATEN_SPEED
        return GHOST_SPEED

    # ------------------------------------------------------------------
    def update(self, dt, maze, pac, blinky, ai_on):
        if self.state == WAITING:
            self.timer -= dt
            if self.timer <= 0:
                self.state = CHASE
            return
        if (self.state == EATEN and self.next_tile is None
                and self.tile == self.start_tile):
            self.state = WAITING          # back home: wait, then return
            self.timer = 1.5
            self.path = []
            return
        self.move(dt, self.speed,
                  lambda: self._choose_next(maze, pac, blinky, ai_on))

    # ------------------------------------------------------------------
    def _target_tile(self, maze, pac, blinky):
        """Which tile is this ghost aiming for while chasing?"""
        pac_tile = pac.current_tile
        if self.name == "Pinky":
            return self._ahead_of_pac(maze, pac, 4)
        if self.name == "Inky":
            a = self._ahead_of_pac(maze, pac, 2)
            b = blinky.current_tile if blinky else pac_tile
            t = (2 * a[0] - b[0], 2 * a[1] - b[1])
            t = (min(max(t[0], 0), maze.width - 1), min(max(t[1], 0), maze.height - 1))
            return t if maze.is_walkable(t, True) else maze.nearest_walkable(t)
        if self.name == "Clyde":
            if manhattan(self.current_tile, pac_tile) > 8:
                return pac_tile
            return self.corner
        return pac_tile                   # Blinky

    @staticmethod
    def _ahead_of_pac(maze, pac, steps):
        t = pac.current_tile
        d = pac.direction
        best = t
        for k in range(1, steps + 1):
            cand = (t[0] + d[0] * k, t[1] + d[1] * k)
            if not maze.is_walkable(cand):
                break
            best = cand
        return best

    def _random_step(self, maze):
        options = maze.neighbors(self.tile, ghost=True)
        forward = [n for n in options if n != self.prev_tile]
        choices = forward or options
        return self.rng.choice(choices) if choices else None

    def _choose_next(self, maze, pac, blinky, ai_on):
        """Called every time the ghost arrives on a tile."""
        nbrs = lambda t: maze.neighbors(t, ghost=True)

        if self.state == EATEN:
            self.path = bfs(self.tile, self.start_tile, nbrs)
            return self.path[1] if len(self.path) > 1 else None

        if self.state == FRIGHTENED or not ai_on:
            self.path = []
            return self._random_step(maze)

        # CHASE with the BFS brain
        target = self._target_tile(maze, pac, blinky)
        if target == self.tile:                    # already there: aim at Pac-Man
            target = pac.current_tile
        blocked = {self.prev_tile} if self.prev_tile else set()  # no U-turns
        path = bfs(self.tile, target, nbrs, blocked)
        if len(path) < 2:
            path = bfs(self.tile, target, nbrs)    # allow a U-turn if stuck
        self.path = path
        if len(path) >= 2:
            return path[1]
        return self._random_step(maze)
