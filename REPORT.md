# Project Report — Smart Pac-Man Ghost AI Using A* and BFS

**Course project · Python / Pygame · Artificial Intelligence (path finding)**

## 1. Objective
Build a playable 2D Pac-Man game in which the characters are controlled by classic search algorithms
instead of a human or a pre-recorded script: **A\*** drives Pac-Man, **BFS** drives the four ghosts.
All algorithms are implemented from scratch with free tools only (Python, Pygame).

## 2. Design
The code is split by responsibility so that each file can be understood on its own:

* `algorithms.py` – generic BFS and A\* (no game knowledge).
* `maze.py` – grid, walls, food, neighbour lookup.
* `entity.py`, `pacman.py`, `ghost.py` – movement and characters.
* `ai_controller.py` – Pac-Man's perception, danger detection and decision rules.
* `game.py`, `ui.py`, `main.py` – rules, interface, dark-themed GUI, program entry.

The maze is a 19 × 21 tile grid; a tile is a `(column, row)` pair. Characters move smoothly between tiles
and request a new target tile each time they arrive on one.

## 3. Methods
**BFS (ghosts).** A queue-based search that expands tiles in rings of increasing distance and therefore
returns a shortest path. Each ghost runs BFS towards its own target tile (Blinky: Pac-Man; Pinky: ahead of Pac-Man;
Inky: mirrored point; Clyde: Pac-Man or his corner depending on distance). BFS is also used as a flood fill to build
the **danger map** (number of steps each ghost needs to reach every tile) and to lead eaten ghosts home.

**A\* (Pac-Man).** Priority-queue search with `f = g + h`, Manhattan-distance heuristic and a cost function that adds
a penalty to tiles close to dangerous ghosts. Pac-Man compares A\* routes to the six nearest foods and takes the cheapest
route that passes a safety test (no ghost can reach any of the next six tiles first).

**Decision system.** Priority rules: hunt frightened ghosts → flee or race to a power pellet when a ghost is within
4 steps → collect a nearby pellet when ghosts are around → collect food. The flee behaviour scores each neighbouring tile
by distance from the closest ghost and by "escape room". Pac-Man can reverse direction mid-step when danger appears, and
the plan is recomputed every time Pac-Man's or a ghost's tile changes.

## 4. Visualisation and interface
Green = Pac-Man's A\* path, white ring = chosen target, red tiles = danger, coloured lines = ghost BFS paths.
The side panel shows the current status, algorithm, target, route length and the state of every ghost.
Controls: Start, Pause/Resume, Restart, AI ON/OFF, Manual/Automatic mode, speed control, path view ON/OFF,
score and lives, Game Over and Victory screens.

## 5. Testing and results
19 automatic tests (`python tests.py`) passed: maze validity; BFS correctness (300 random pairs vs. an independent
flood fill); A\* equals BFS on equal costs and avoids expensive tiles; game launch and all screens; buttons and
keyboard; automatic food collection; BFS chasing; fleeing; no crash or freeze in all mode combinations and after a
2-second lag spike.

Comparison over 6 games of up to 120 s each (the "AI OFF" baseline makes Pac-Man and the ghosts wander randomly):

| | Wins | Avg. deaths | Avg. food eaten (of 150) |
|---|---|---|---|
| AI ON (A\* + BFS) | 4 / 6 | 1.5 | 144 |
| AI OFF (random) | 0 / 6 | 3.0 | 112 |

Average processing time per frame (update + drawing) was about 2.4 ms, well inside the 16.7 ms budget for 60 FPS.

## 6. Limitations
* Tested in a headless environment (logic, rendering to screenshots) – not on a physical Windows machine.
* Pac-Man is not perfect: it reacts to where ghosts *are* and to their BFS distances, but does not predict their
  future routes, so it can still be cornered (2 of 6 test games were not won).
* Simplified rules compared with the arcade original: one maze, no tunnels, no fruit, no levels, no sound.
* The Manhattan heuristic ignores walls, so A\* may expand more tiles than with a better heuristic (it remains correct).

## 7. Conclusion
A\* and BFS genuinely control the movement of all five characters. Danger-aware A\* plus a safety check lets Pac-Man collect food
and avoid ghosts far better than random movement, while BFS gives the ghosts efficient, differentiated chasing behaviour. The
project shows the practical difference between an uninformed search (BFS), good for shortest paths on equal costs,
and an informed, cost-aware search (A\*), good for goal-directed movement with risk.

## 8. Possible future work
Ghost-movement prediction, a learned heuristic, multiple levels, sound, high-score table, and comparing other algorithms
(DFS, Dijkstra, Greedy best-first) in the same visualiser.

---
### Presentation outline (8 slides)
1. Title and goal · 2. Game overview (screenshot) · 3. BFS explained (water analogy) · 4. A\* explained (f = g + h)
5. Pac-Man decision flow (sense → danger → choose → safety check) · 6. Ghost personalities · 7. Live demo with path view ON/OFF
and AI ON/OFF · 8. Results table, limitations, future work.
