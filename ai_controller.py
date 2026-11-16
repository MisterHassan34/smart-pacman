"""
ai_controller.py - Pac-Man's brain.

Every time Pac-Man needs to choose a direction, `decide()` runs this routine:

 1. SENSE      Where is Pac-Man? Where are the ghosts? Where is the food?
 2. DANGER     For every dangerous ghost run a BFS flood-fill to learn how many
               steps it needs to reach each tile. Tiles within DANGER_RADIUS
               steps of a ghost become "dangerous tiles" (shown in red).
 3. DECIDE     Pick the first rule that applies:
                 a) Power pellet active + frightened ghost nearby -> HUNT it (A*)
                 b) Ghost very close -> run to a power pellet if it is safely
                    reachable (A*), otherwise FLEE (safety scoring)
                 c) Ghosts around and a pellet is close and safe -> grab it (A*)
                 d) Otherwise -> go to the best nearby FOOD (A*)
 4. SAFETY     Every A* route is checked: would a ghost be able to reach any of
               the next few tiles before Pac-Man does? If so, the route is
               rejected and Pac-Man changes direction.
 5. REPEAT     decide() is called again whenever the situation changes
               (a ghost moved to another tile, food was eaten, Pac-Man moved).

A* gets a "cost function" that makes dangerous tiles expensive, so even when a
route is allowed it prefers to keep away from ghosts.
"""

import random
from algorithms import astar, bfs_distances, manhattan
from ghost import CHASE, FRIGHTENED
from pacman import PAC_SPEED

DANGER_RADIUS = 3       # tiles within this many ghost-steps are "dangerous"
THREAT_DISTANCE = 4     # a ghost this close (in steps) triggers panic mode
DANGER_COST = 8         # extra A* cost per danger level of a tile
SAFETY_HORIZON = 6      # how many upcoming tiles are checked for safety
FOOD_CANDIDATES = 6     # how many nearby foods are compared with A*


class PacmanAI:
    def __init__(self, maze, rng=None):
        self.maze = maze
        self.rng = rng or random.Random()
        self._pac_nbrs = lambda t: maze.neighbors(t, ghost=False)
        self._ghost_nbrs = lambda t: maze.neighbors(t, ghost=True)
        self._sig = None
        self._result = None
        self.clear()

    # ------------------------------------------------------------------
    def clear(self):
        """Forget the current plan (used when the AI is not in control)."""
        self.status = "Idle"
        self.algorithm = "-"
        self.target = None
        self.target_label = "-"
        self.path = []
        self.danger_tiles = {}
        self.threat = False
        self._sig = None
        self._result = None

    # ------------------------------------------------------------------
    def decide(self, pac, ghosts, power_left):
        """Return the next tile Pac-Man should walk to (or None)."""
        start = pac.tile
        sig = (start,
               tuple((g.current_tile, g.state) for g in ghosts),
               len(self.maze.dots), len(self.maze.pellets), int(power_left * 2))
        if sig == self._sig:               # nothing changed: keep the plan
            return self._result
        self._sig = sig
        self._result = self._think(start, ghosts, power_left)
        return self._result

    def random_step(self, pac):
        """Used when the AI switch is OFF: wander without thinking."""
        self.clear()
        self.status = "AI OFF - random walk"
        self.algorithm = "None (random)"
        options = self._pac_nbrs(pac.tile)
        forward = [n for n in options if n != pac.prev_tile]
        choices = forward or options
        return self.rng.choice(choices) if choices else None

    # ------------------------------------------------------------------
    def _think(self, start, ghosts, power_left):
        maze = self.maze
        dangerous = [g for g in ghosts if g.state == CHASE]
        scared = [g for g in ghosts if g.state == FRIGHTENED]

        # 2. DANGER MAP: BFS flood-fill from every dangerous ghost
        gdists = [bfs_distances(g.current_tile, self._ghost_nbrs) for g in dangerous]
        danger = {}
        for dist in gdists:
            for tile, d in dist.items():
                if d <= DANGER_RADIUS:
                    danger[tile] = max(danger.get(tile, 0), DANGER_RADIUS + 1 - d)
        self.danger_tiles = danger
        nearest = min((d.get(start, 99) for d in gdists), default=99)
        self.threat = nearest <= THREAT_DISTANCE

        cost_fn = lambda t: DANGER_COST * danger.get(t, 0)
        # Tiles right next to a ghost are never used if another way exists
        blocked = {t for t, lvl in danger.items() if lvl >= 3 and t != start}

        def plan(goal):
            path, cost = astar(start, goal, self._pac_nbrs, cost_fn, blocked)
            if not path:
                path, cost = astar(start, goal, self._pac_nbrs, cost_fn)
            return path, cost

        # a) HUNT frightened ghosts while the power-up lasts
        if scared and power_left > 2:
            reachable = (power_left - 1.0) * PAC_SPEED * 0.7
            for g in sorted(scared, key=lambda g: manhattan(start, g.current_tile))[:2]:
                path, _ = plan(g.current_tile)
                if len(path) > 1 and len(path) - 1 <= reachable and self._safe(path, gdists):
                    return self._follow(path, g.current_tile, "HUNTING frightened ghost",
                                        "A* + danger cost", f"Ghost {g.name}")

        # b) a ghost is close: power pellet if safely reachable, else flee
        if self.threat:
            res = self._try_pellet(plan, start, gdists, max_len=10,
                                   status="RACING to power pellet (danger!)")
            return res or self._flee(start, gdists)

        # c) ghosts around and a pellet is close and safe: collect it
        if dangerous and power_left <= 0 and nearest <= 8:
            res = self._try_pellet(plan, start, gdists, max_len=8,
                                   status="Collecting power pellet (ghosts near)")
            if res:
                return res

        # d) normal life: A* to the best nearby food
        foods = maze.dots if maze.dots else maze.pellets
        if not foods:
            self.clear()
            return None
        candidates = sorted(foods, key=lambda f: manhattan(start, f))[:FOOD_CANDIDATES]
        options = []
        for food in candidates:
            path, cost = plan(food)
            if len(path) > 1:
                options.append((cost, path, food))
        options.sort(key=lambda o: o[0])
        for cost, path, food in options:       # cheapest SAFE route wins
            if self._safe(path, gdists):
                return self._follow(path, food, "Collecting food",
                                    "A* + danger cost", f"Food {food}")
        if dangerous:                          # every route is risky -> flee
            return self._flee(start, gdists)
        return self._flee(start, gdists) if not options else self._follow(
            options[0][1], options[0][2], "Collecting food",
            "A* + danger cost", f"Food {options[0][2]}")

    # ------------------------------------------------------------------
    def _follow(self, path, target, status, algorithm, label):
        self.path = path
        self.target = target
        self.target_label = label
        self.status = status
        self.algorithm = algorithm
        return path[1]

    def _try_pellet(self, plan, start, gdists, max_len, status):
        for p in sorted(self.maze.pellets, key=lambda p: manhattan(start, p))[:2]:
            path, _ = plan(p)
            if 1 < len(path) <= max_len + 1 and self._safe(path, gdists):
                return self._follow(path, p, status, "A* + danger cost", f"Pellet {p}")
        return None

    @staticmethod
    def _safe(path, gdists):
        """
        Safety check: Pac-Man reaches path[i] after i steps. If any ghost can
        reach that tile in i steps or fewer, the route is NOT safe.
        """
        for i, tile in enumerate(path[1:SAFETY_HORIZON + 1], start=1):
            for dist in gdists:
                if dist.get(tile, 99) <= i:
                    return False
        return True

    def _flee(self, start, gdists):
        """
        Panic mode: look at every neighbouring tile and score it.
          + far away from the closest ghost (BFS distance)
          + lots of "escape room" (tiles Pac-Man can reach before any ghost)
          - big penalty for stepping right next to a ghost
        """
        options = self._pac_nbrs(start)
        if not options:
            self.clear()
            return None
        best, best_score = None, -1e9
        for n in options:
            dmin = min((d.get(n, 99) for d in gdists), default=99)
            reach = bfs_distances(n, self._pac_nbrs, max_depth=8)
            room = sum(1 for t, steps in reach.items()
                       if all(d.get(t, 99) > steps + 1 for d in gdists))
            score = min(dmin, 12) * 3 + min(room, 40) * 0.6
            if n in self.maze.dots:
                score += 2
            if dmin <= 1:
                score -= 50
            if score > best_score:
                best, best_score = n, score
        self.path = [start, best]
        self.target = None
        self.target_label = "none (running away)"
        self.status = "FLEEING - ghost too close!"
        self.algorithm = "BFS + escape scoring"
        return best
