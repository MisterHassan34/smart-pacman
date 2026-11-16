"""
pacman.py - The Pac-Man character.

Pac-Man itself does not "think". Someone else tells it where to go:
  * Automatic mode -> ai_controller.PacmanAI (A* based)
  * Manual mode    -> the keyboard (see manual_choice below)
"""

from entity import Mover

PAC_SPEED = 5.2  # tiles per second at normal game speed


class PacMan(Mover):
    def reset(self):
        super().reset()
        self.desired = (0, 0)   # direction the player is asking for (manual)

    def request_direction(self, direction):
        """Keyboard input. Reversing in the middle of a step is allowed."""
        self.desired = direction
        if (self.next_tile is not None and
                direction == (-self.direction[0], -self.direction[1])):
            self.reverse()

    def manual_choice(self, maze):
        """Keyboard logic: try the wanted direction, else keep going straight."""
        for d in (self.desired, self.direction):
            if d != (0, 0):
                target = (self.tile[0] + d[0], self.tile[1] + d[1])
                if maze.is_walkable(target):
                    return target
        return None

    def update(self, dt, choose_next):
        self.move(dt, PAC_SPEED, choose_next)
