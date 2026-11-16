"""
algorithms.py - The two path-finding algorithms, written from scratch.

BFS (Breadth First Search)
    Explores the maze in "rings": first every tile 1 step away, then every tile
    2 steps away, and so on. The first time it reaches the goal, that path is
    guaranteed to be the SHORTEST one (when every step costs the same).
    -> Used by the GHOSTS to chase Pac-Man.

A* (A-star)
    Like BFS, but it is "smart": it prefers tiles that look closer to the goal
    (using a guess called the heuristic) and it understands that some tiles are
    more "expensive" than others (for example, tiles close to a ghost).
    -> Used by PAC-MAN to reach food while avoiding danger.

Both functions are generic: they do not know anything about Pac-Man. You give
them a `neighbors_fn(tile)` that returns the tiles you can walk to from `tile`.
A tile is just a (column, row) tuple.
"""

from collections import deque
import heapq


def manhattan(a, b):
    """Distance if you could only move up/down/left/right, ignoring walls."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _rebuild_path(came_from, end):
    """Follow the 'came_from' links backwards to build start -> end path."""
    path = [end]
    while came_from[path[-1]] is not None:
        path.append(came_from[path[-1]])
    path.reverse()
    return path


# --------------------------------------------------------------------------
# BFS
# --------------------------------------------------------------------------
def bfs(start, goal, neighbors_fn, blocked=None):
    """
    Shortest path from `start` to `goal` using Breadth First Search.

    blocked: optional set of tiles that must not be used (the ghosts use this
             to avoid turning around 180 degrees).
    Returns a list of tiles [start, ..., goal], or [] if there is no path.
    """
    if start == goal:
        return [start]
    blocked = blocked or set()
    came_from = {start: None}          # also acts as the "visited" set
    queue = deque([start])             # FIFO queue = explore ring by ring
    while queue:
        current = queue.popleft()
        for nxt in neighbors_fn(current):
            if nxt in came_from or nxt in blocked:
                continue
            came_from[nxt] = current
            if nxt == goal:
                return _rebuild_path(came_from, nxt)
            queue.append(nxt)
    return []


def bfs_distances(start, neighbors_fn, max_depth=None):
    """
    BFS "flood fill": returns {tile: number_of_steps_from_start} for every tile
    that can be reached. Pac-Man's safety system uses this to know how many
    steps each ghost needs to reach any tile of the maze.
    """
    dist = {start: 0}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        if max_depth is not None and dist[current] >= max_depth:
            continue
        for nxt in neighbors_fn(current):
            if nxt not in dist:
                dist[nxt] = dist[current] + 1
                queue.append(nxt)
    return dist


# --------------------------------------------------------------------------
# A*
# --------------------------------------------------------------------------
def astar(start, goal, neighbors_fn, cost_fn=None, blocked=None):
    """
    Cheapest path from `start` to `goal` using A*.

    f(tile) = g(tile) + h(tile)
        g = real cost paid so far (1 per step + extra danger cost of the tile)
        h = Manhattan distance to the goal (an optimistic guess)
    The tile with the smallest f is always explored next.

    cost_fn(tile) -> extra cost for stepping on `tile` (>= 0). Never negative,
                     so the Manhattan heuristic stays "optimistic" and A* stays
                     correct.
    Returns (path, total_cost). If there is no path: ([], infinity).
    """
    if start == goal:
        return [start], 0
    blocked = blocked or set()
    counter = 0                                   # tie-breaker for the heap
    open_heap = [(manhattan(start, goal), counter, start)]
    came_from = {start: None}
    g_cost = {start: 0}
    closed = set()
    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        if current == goal:
            return _rebuild_path(came_from, current), g_cost[current]
        if current in closed:
            continue
        closed.add(current)
        for nxt in neighbors_fn(current):
            if nxt in blocked or nxt in closed:
                continue
            step = 1 + (cost_fn(nxt) if cost_fn else 0)
            new_g = g_cost[current] + step
            if new_g < g_cost.get(nxt, float("inf")):
                g_cost[nxt] = new_g
                came_from[nxt] = current
                counter += 1
                heapq.heappush(open_heap, (new_g + manhattan(nxt, goal), counter, nxt))
    return [], float("inf")
