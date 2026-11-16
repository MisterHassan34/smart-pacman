# Smart Pac-Man AI — A* and BFS

A complete 2D Pac-Man game written in Python and Pygame where **Pac-Man plays by itself using A\***
and **the four ghosts chase him using BFS**. Both algorithms are written from scratch (no
path-finding libraries, no paid APIs, no external AI services). Everything is free.

```
Smart-Pacman-AI/
    main.py            starts the game
    game.py            game rules, drawing, buttons, main loop
    pacman.py          the Pac-Man character
    ghost.py           the ghosts (BFS chasers)
    maze.py            the maze layout, walls, food
    algorithms.py      BFS and A* (from scratch)
    ai_controller.py   Pac-Man's brain (A* + danger detection)
    entity.py          smooth tile-to-tile movement shared by all characters
    ui.py              dark theme colours and the Button widget
    tests.py           automatic tests (19 tests)
    requirements.txt   the one dependency: pygame
    README.md          this file
    REPORT.md          short project report + presentation notes
    assets/            empty on purpose: all graphics are drawn by code
```

---

## 1. Installation on Windows

1. **Install Python 3.9 or newer** from <https://www.python.org/downloads/>.
   On the first installer screen, tick **"Add python.exe to PATH"**, then click *Install Now*.
2. Check it worked. Open *Command Prompt* (press `Win`, type `cmd`) and run:
   ```
   python --version
   ```
3. Put the `Smart-Pacman-AI` folder somewhere easy, for example `C:\Projects\Smart-Pacman-AI`.
4. Install the requirement:
   ```
   cd C:\Projects\Smart-Pacman-AI
   pip install -r requirements.txt
   ```
   (If `pip` is not recognised, use `python -m pip install -r requirements.txt`.)

## 2. VS Code setup

1. Install VS Code from <https://code.visualstudio.com/>.
2. Open VS Code → **Extensions** (`Ctrl+Shift+X`) → install **Python** (by Microsoft).
3. **File → Open Folder…** → choose `Smart-Pacman-AI`.
4. Press `Ctrl+Shift+P` → **Python: Select Interpreter** → pick the Python you installed.
5. (Optional but tidy) create a virtual environment in the VS Code terminal (`` Ctrl+` ``):
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
   If PowerShell blocks `activate`, run once:
   `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
6. Open `main.py` and press the ▶ **Run** button (top right), or type in the terminal:
   ```
   python main.py
   ```

## 3. Commands

| What | Command |
|---|---|
| Run the game | `python main.py` |
| Run the automatic tests | `python tests.py` |

## 4. How to play / controls

| Control | Action |
|---|---|
| **Start Game** button / `ENTER` | start a new game |
| **Pause / Resume** / `SPACE` | pause |
| **Restart** / `R` | restart |
| **AI: ON/OFF** / `I` | ON = smart A\*/BFS. OFF = Pac-Man *and* ghosts move randomly (a baseline so you can see how much the AI matters) |
| **Mode: AUTO/MANUAL** / `M` | AUTO = the AI drives Pac-Man. MANUAL = you drive with arrow keys or `WASD` (the ghosts still chase with BFS) |
| **Path view: ON/OFF** / `V` | show or hide the AI visualisation |
| **− / +** / `-` `+` | game speed 0.5x … 3x |
| `ESC` | quit |

Scoring: dot = 10, power pellet = 50, frightened ghost = 200 → 400 → 800 → 1600. You have 3 lives.
Eat all 150 pieces of food to win.

### What the colours mean (Path view ON)
* **Green line** – Pac-Man's planned A\* path. The **white pulsing ring** is the chosen target.
* **Red squares** – dangerous tiles (within 3 ghost-steps of a dangerous ghost; darker = closer).
* **Coloured lines** – each ghost's current BFS path, in that ghost's colour.
* **Right panel** – current status, algorithm in use, target, route length and what each ghost is doing.

---

## 5. Explanation of every file

**`algorithms.py`** – the heart of the project. Contains `bfs()`, `bfs_distances()` (a BFS "flood
fill") and `astar()`. They know nothing about Pac-Man: you give them a function that lists the
neighbours of a tile, and they return a path. That makes them easy to test and reuse.

**`maze.py`** – the maze is a list of text rows (`#` wall, `.` dot, `o` power pellet, `-` ghost
door, `P` Pac-Man). The `Maze` class turns it into sets of tiles and answers questions such as
"is this tile walkable?" and "who are my neighbours?". The ghost door can only be passed by ghosts.

**`entity.py`** – movement. Characters live on a grid but are drawn smoothly between tiles. The
class `Mover` stores `tile`, `next_tile` and `progress` (0 → 1). When a character reaches a tile it
asks a "chooser" function where to go next. For Pac-Man that chooser is the AI (or the keyboard); for
ghosts it is BFS.

**`pacman.py`** – Pac-Man's speed and keyboard handling. It contains no AI: it just walks where it is told.

**`ghost.py`** – the `Ghost` class: four states (waiting, chase, frightened, eaten) and BFS chasing.
Each ghost has a different target (see section 7).

**`ai_controller.py`** – `PacmanAI`: the danger detection and decision system (see section 6).

**`game.py`** – the `Game` class. `update()` contains the rules (movement, eating, collisions, lives,
power-ups, winning); `draw()` draws everything including the AI visualisation; `run()` is the main loop.

**`ui.py`** – colours for the dark theme and the `Button` class.

**`main.py`** – creates the window and starts the game; prints a friendly message if Pygame is missing.

**`tests.py`** – 19 automatic tests that run without a window (see section 9).

---

## 6. How Pac-Man's AI makes decisions

Whenever Pac-Man arrives on a new tile (and also whenever a ghost changes tile) `PacmanAI.decide()` runs:

1. **Sense.** Read Pac-Man's tile, every ghost's tile and state, and the remaining food.
2. **Danger map (BFS).** For each *dangerous* ghost (state CHASE) run a BFS flood-fill to learn how many
   steps it needs to reach every tile. Tiles within 3 steps become *dangerous tiles* (shown red).
3. **Choose a goal** – the first rule that fits:
   * **Hunt** – a power pellet is active and a frightened ghost is reachable in time → A\* to the ghost.
   * **Panic** – a ghost is within 4 steps → run to a power pellet if A\* finds a *safe* route; otherwise **flee**.
   * **Power pellet** – ghosts are around (≤ 8 steps), a pellet is close and the route is safe → grab it.
   * **Food** – compare A\* routes to the 6 nearest foods and take the cheapest safe one.
4. **A\* with danger costs.** Each dangerous tile adds +8 cost per danger level, and tiles right next
   to a ghost are blocked. So even a "legal" route prefers to stay away from ghosts.
5. **Safety check.** Pac-Man reaches the i-th tile of a route after *i* steps. If any ghost can reach that
   tile in *i* steps or fewer (looking at the next 6 tiles), the route is rejected.
6. **Flee scoring.** Each neighbouring tile gets a score: *distance from the nearest ghost* + *"escape room"*
   (how many tiles Pac-Man can reach before any ghost) − a big penalty for stepping next to a ghost.
7. **Change direction.** In the first half of a step Pac-Man can turn around immediately if danger appears.
8. **Repeat** – continuously, whenever the situation changes.

The path shown in green is exactly the path Pac-Man follows: `decide()` returns `path[1]`, the next tile,
and `Mover.move()` walks there. The AI genuinely controls the movement.

## 7. How the ghosts behave (BFS)

Every ghost, each time it arrives on a tile, runs `bfs(own_tile, target)` and steps to the second tile of the path.
They cannot make 180° turns (so they do not jitter), but they differ in *what they aim at*:

| Ghost | Target tile |
|---|---|
| Blinky (red) | Pac-Man's tile — direct chase |
| Pinky (pink) | up to 4 tiles *ahead* of Pac-Man — an ambusher |
| Inky (cyan) | a point mirrored through a spot 2 tiles ahead of Pac-Man, relative to Blinky |
| Clyde (orange) | Pac-Man when far (> 8 tiles), his corner when close — the shy one |

Ghosts are released from the house at 0 s, 2 s, 5 s and 8 s. After a power pellet they turn blue,
slow down and wander randomly; if eaten, BFS leads their eyes back to the house.

---

## 8. A\* and BFS in simple language (for your presentation)

### BFS — Breadth First Search
Imagine pouring water into a maze. It spreads in every direction at the same speed. The first time the
water touches the goal, the route it took is the **shortest** one.
* Uses a **queue** (first in, first out): explore every tile 1 step away, then 2 steps away, then 3 …
* Always finds the shortest path when every step costs the same. Complexity O(V + E).
* **Used for:** ghosts chasing Pac-Man, and the danger map ("how far is each ghost from each tile?").

### A\* — "A-star"
BFS explores in all directions, even away from the goal. A\* is BFS with **common sense**: it uses
`f = g + h`
* `g` = real cost so far (1 per step + danger penalty),
* `h` = a guess of the remaining distance (here: Manhattan distance |Δx| + |Δy|, which never over-estimates),
* it always explores the tile with the smallest `f` first (a **priority queue**).

Because the heuristic never over-estimates, A\* still finds the cheapest path but looks at far fewer tiles.
Because tiles can have **different costs**, A\* can steer Pac-Man around dangerous areas, which plain BFS cannot.
* **Used for:** Pac-Man walking to food, power pellets and frightened ghosts.

| | BFS | A\* |
|---|---|---|
| Data structure | queue | priority queue |
| Tile costs | all equal | can differ (danger!) |
| Knows where the goal is | no | yes (heuristic) |
| Result | shortest path | cheapest path |
| In this project | ghosts + danger map | Pac-Man |

---

## 9. Testing — what was really tested

`python tests.py` runs 19 tests with no window (Pygame's "dummy" video driver):

* Maze is valid; all food is reachable; ghosts can reach Pac-Man from their start tiles; Pac-Man cannot use the ghost door.
* **BFS** returns valid, shortest paths on 300 random pairs (checked against an independent flood-fill).
* **A\*** gives the same length as BFS when costs are equal (300 pairs), and detours around expensive tiles.
* The game launches and every screen (menu, playing, paused, game over, victory) draws without error.
* All buttons and keyboard keys work (simulated mouse clicks and key presses).
* **Pac-Man moves automatically and collects food** via A\*; the A\* path really starts at Pac-Man's tile and ends at the target.
* **Ghosts chase with BFS** (Blinky gets closer to a standing Pac-Man) and have different targets.
* **Pac-Man flees** a ghost that is 3 tiles away instead of walking towards it.
* **No freezing/crashing** in all four combinations of AUTO/MANUAL × AI ON/OFF over 40 s of game time, and after a simulated 2-second lag spike.
* **AI vs. no AI** (6 games each, up to 120 s): results from my run:

  | | Wins | Average deaths | Average food eaten (of 150) |
  |---|---|---|---|
  | AI ON | 4 / 6 | 1.5 | 144 |
  | AI OFF | 0 / 6 | 3.0 (always game over) | 112 |

  Average frame time was about 2.4 ms (the 60 FPS budget is 16.7 ms).

**Honest limits.** The tests were run in a headless environment, so I verified behaviour, logic and rendering
(I looked at screenshots), but I could not physically play it on a Windows machine with a real monitor. The AI is
strong but not perfect: it can still be trapped (it won 4 of 6 test games, not all of them). Because the ghosts are
slightly slower than Pac-Man and chase differently, results vary from run to run.

## 10. Troubleshooting

* **`'python' is not recognized`** → reinstall Python and tick *Add python.exe to PATH*.
* **`No module named pygame`** → run `pip install -r requirements.txt` in the project folder.
* **Window too big for a small screen** → the window is 880 × 664 pixels; lower your Windows display scaling.
* **Too fast or too slow** → use the `−` / `+` speed buttons.

## 11. Ideas to extend it
Add sound effects, more levels (new `LAYOUT`s in `maze.py`), a high-score file, or make Pac-Man predict where ghosts
will be (not just where they are now).
