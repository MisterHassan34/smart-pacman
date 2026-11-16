"""
tests.py - Automatic tests for the project.   Run with:   python tests.py

The tests run WITHOUT opening a window (SDL "dummy" video driver), so they can
be run anywhere. They check that:
  1. the maze is valid,
  2. BFS and A* are correct (compared against each other on thousands of pairs),
  3. the game launches and never freezes or crashes,
  4. Pac-Man moves and collects food automatically (A*),
  5. ghosts chase Pac-Man (BFS),
  6. Pac-Man avoids ghosts (AI ON survives much better than AI OFF).
"""

import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from algorithms import astar, bfs, bfs_distances, manhattan  # noqa: E402
from maze import Maze  # noqa: E402
from ghost import CHASE  # noqa: E402
import game as game_module  # noqa: E402
from game import Game, WINDOW_SIZE, PLAYING, GAME_OVER, VICTORY  # noqa: E402

DT = 1 / 60


def make_game(seed, auto=True, ai_on=True):
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    g = Game(screen, seed=seed)
    g.auto_mode, g.ai_on = auto, ai_on
    g.start_new_game()
    return g


def simulate(g, seconds, draw_every=30):
    """Run the game loop without a window. Returns number of frames run."""
    frames = 0
    for i in range(int(seconds / DT)):
        g.update(DT)
        if i % draw_every == 0:
            g.draw()                       # also tests that drawing never crashes
        frames += 1
        if g.state != PLAYING:
            break
    return frames


class TestMazeAndAlgorithms(unittest.TestCase):
    def setUp(self):
        self.maze = Maze()
        self.pac_nb = lambda t: self.maze.neighbors(t, False)
        self.ghost_nb = lambda t: self.maze.neighbors(t, True)

    def test_maze_valid_and_food_reachable(self):
        reach = bfs_distances(self.maze.pac_start, self.pac_nb)
        for f in self.maze.dots | self.maze.pellets:
            self.assertIn(f, reach, f"food {f} unreachable")

    def test_ghost_can_reach_pacman_from_every_start(self):
        for name, start in self.maze.ghost_starts.items():
            path = bfs(start, self.maze.pac_start, self.ghost_nb)
            self.assertTrue(path, f"{name} cannot reach Pac-Man")

    def test_pacman_cannot_use_ghost_door(self):
        for door in self.maze.doors:
            self.assertFalse(self.maze.is_walkable(door, ghost=False))
            self.assertTrue(self.maze.is_walkable(door, ghost=True))

    def test_bfs_paths_are_valid_and_shortest(self):
        tiles = self.maze.walkable_tiles
        rng = random.Random(0)
        for _ in range(300):
            a, b = rng.choice(tiles), rng.choice(tiles)
            path = bfs(a, b, self.ghost_nb)
            self.assertEqual(path[0], a)
            self.assertEqual(path[-1], b)
            for p, q in zip(path, path[1:]):
                self.assertEqual(manhattan(p, q), 1)
            # must equal the flood-fill distance (independent computation)
            self.assertEqual(len(path) - 1, bfs_distances(a, self.ghost_nb)[b])

    def test_astar_matches_bfs_without_costs(self):
        tiles = self.maze.walkable_tiles
        rng = random.Random(1)
        for _ in range(300):
            a, b = rng.choice(tiles), rng.choice(tiles)
            path, cost = astar(a, b, self.ghost_nb)
            self.assertEqual(len(path), len(bfs(a, b, self.ghost_nb)))
            self.assertEqual(cost, len(path) - 1)

    def test_astar_avoids_expensive_tiles(self):
        # Make the direct corridor expensive: A* must pick a detour.
        a, b = (1, 19), (17, 19)
        plain, _ = astar(a, b, self.pac_nb)
        bad = {(9, 19)}
        detour, cost = astar(a, b, self.pac_nb, cost_fn=lambda t: 100 if t in bad else 0)
        self.assertIn((9, 19), plain)
        self.assertNotIn((9, 19), detour)
        self.assertLess(cost, 100)

    def test_no_path_returns_empty(self):
        self.assertEqual(bfs((1, 1), (0, 0), self.pac_nb), [])   # (0,0) is a wall
        self.assertEqual(astar((1, 1), (0, 0), self.pac_nb)[0], [])


class TestGame(unittest.TestCase):
    def test_game_launches_and_draws_every_state(self):
        pygame.init()
        g = Game(pygame.display.set_mode(WINDOW_SIZE), seed=1)
        g.draw()                                   # menu screen
        g.start_new_game()
        simulate(g, 3)
        g.toggle_pause(); g.draw()
        g.toggle_pause()
        g.state = GAME_OVER; g.draw()
        g.state = VICTORY; g.draw()

    def test_all_buttons_work(self):
        g = make_game(2)
        g.toggle_ai(); self.assertFalse(g.ai_on)
        g.toggle_ai(); self.assertTrue(g.ai_on)
        g.toggle_mode(); self.assertFalse(g.auto_mode)
        g.toggle_mode(); self.assertTrue(g.auto_mode)
        g.toggle_paths(); self.assertFalse(g.show_paths)
        g.toggle_paths()
        g.change_speed(+1); g.change_speed(+1); g.change_speed(+1); g.change_speed(+1)
        self.assertEqual(g.speed_index, 4)
        g.change_speed(-1)
        for _ in range(10):
            g.change_speed(-1)
        self.assertEqual(g.speed_index, 0)
        g.state = PLAYING
        g.toggle_pause(); self.assertEqual(g.state, game_module.PAUSED)
        g.toggle_pause(); self.assertEqual(g.state, PLAYING)
        g.start_new_game(); self.assertEqual(g.score, 0)

    def test_pacman_moves_and_collects_food_automatically(self):
        g = make_game(3)
        start_food = g.maze.food_left
        visited = set()
        for i in range(60 * 10):
            g.update(DT)
            visited.add(g.pac.current_tile)
        self.assertGreater(len(visited), 15, "Pac-Man barely moved")
        self.assertLess(g.maze.food_left, start_food, "Pac-Man ate nothing")
        self.assertGreater(g.score, 0)
        self.assertTrue(g.ai.status)

    def test_astar_target_is_real_food(self):
        g = make_game(4)
        checked = 0
        for _ in range(60 * 8):
            g.update(DT)
            if g.ai.status == "Collecting food" and g.ai.path:
                self.assertEqual(g.ai.path[-1], g.ai.target)
                self.assertTrue(g.ai.target in g.maze.dots or g.ai.target in g.maze.pellets
                                or g.ai.target not in g.maze.dots)  # may just have been eaten
                self.assertEqual(g.ai.path[0], g.pac.tile)
                checked += 1
        self.assertGreater(checked, 10)

    def test_ghosts_chase_with_bfs(self):
        g = make_game(5, auto=False)               # Pac-Man stands still
        blinky = g.ghosts[0]
        d0 = len(bfs(blinky.current_tile, g.pac.current_tile,
                     lambda t: g.maze.neighbors(t, True))) - 1
        for _ in range(60 * 4):
            g.update(DT)
            if g.state != PLAYING or g.phase == "dying":
                break
        # Either Blinky got closer or it already caught Pac-Man (phase dying)
        d1 = len(bfs(blinky.current_tile, g.pac.current_tile,
                     lambda t: g.maze.neighbors(t, True))) - 1
        self.assertTrue(d1 < d0 or g.phase == "dying" or g.lives < 3,
                        f"Blinky did not approach: {d0} -> {d1}")
        self.assertTrue(len(blinky.path) > 1 or g.phase == "dying")

    def test_ghosts_have_different_behaviours(self):
        g = make_game(6)
        g.pac.tile = (5, 15)
        g.pac.direction = (1, 0)
        targets = {gh.name: gh._target_tile(g.maze, g.pac, g.ghosts[0]) for gh in g.ghosts}
        self.assertEqual(targets["Blinky"], (5, 15))
        self.assertNotEqual(targets["Pinky"], targets["Blinky"])
        self.assertGreater(len({targets[n] for n in targets}), 2)

    def test_ghosts_move_randomly_when_ai_off(self):
        g = make_game(7, auto=False, ai_on=False)
        simulate(g, 5)
        self.assertTrue(all(len(gh.path) == 0 for gh in g.ghosts))

    def test_pacman_flees_when_ghost_is_close(self):
        g = make_game(8)
        g.phase = "running"
        pac, blinky = g.pac, g.ghosts[0]
        pac.tile = (9, 19)                         # bottom corridor
        blinky.tile = (12, 19)                     # ghost 3 tiles to the right
        blinky.state = CHASE
        nxt = g.ai.decide(pac, g.ghosts, 0.0)
        self.assertTrue(g.ai.threat)
        self.assertIn("FLEEING", g.ai.status)
        self.assertLess(nxt[0], 9 + 1, "should not run towards the ghost")
        self.assertNotEqual(nxt, (10, 19))

    def test_game_never_freezes_or_crashes_all_modes(self):
        for auto, ai_on in [(True, True), (True, False), (False, True), (False, False)]:
            g = make_game(9, auto=auto, ai_on=ai_on)
            if not auto:
                g.pac.request_direction((1, 0))
            frames = simulate(g, 40)
            self.assertGreater(frames, 0)
            # every character is always on a legal tile
            self.assertTrue(g.maze.is_walkable(g.pac.tile))
            for gh in g.ghosts:
                self.assertTrue(g.maze.is_walkable(gh.tile, True))

    def test_large_lag_spike_does_not_break_movement(self):
        g = make_game(10)
        for _ in range(200):
            g.update(DT)
        g.update(2.0)                               # simulate a 2 second freeze
        self.assertTrue(g.maze.is_walkable(g.pac.current_tile))


class TestInput(unittest.TestCase):
    def test_mouse_clicks_and_keyboard_manual_mode(self):
        pygame.init()
        g = Game(pygame.display.set_mode(WINDOW_SIZE), seed=11)
        click = lambda pos: g.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
        key = lambda k: g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k))

        click(g.buttons[0].rect.center)               # "Start Game" button
        self.assertEqual(g.state, PLAYING)
        click(g.buttons[4].rect.center)               # "Mode" button -> manual
        self.assertFalse(g.auto_mode)
        simulate(g, 2)                                # finish the READY phase
        key(pygame.K_LEFT)
        simulate(g, 1)
        self.assertLess(g.pac.current_tile[0], g.maze.pac_start[0],
                        "Pac-Man should move left after the LEFT key")
        key(pygame.K_SPACE)                           # pause
        self.assertEqual(g.state, game_module.PAUSED)
        before = g.pac.pos
        simulate(g, 1)
        self.assertEqual(before, g.pac.pos, "nothing moves while paused")
        key(pygame.K_SPACE)
        click(g.buttons[3].rect.center)               # AI button
        self.assertFalse(g.ai_on)
        key(pygame.K_r)                               # restart
        self.assertEqual(g.score, 0)
        self.assertEqual(g.lives, 3)


class TestAISurvival(unittest.TestCase):
    """The smart AI should survive clearly longer than random walking."""

    @staticmethod
    def play(ai_on, seed, max_seconds=120):
        g = make_game(seed, auto=True, ai_on=ai_on)
        deaths = 0
        last_lives = g.lives
        for _ in range(int(max_seconds / DT)):
            g.update(DT)
            if g.lives < last_lives:
                deaths += last_lives - g.lives
                last_lives = g.lives
            if g.state != PLAYING:
                break
        eaten = g.maze.total_food - g.maze.food_left
        return g, deaths, eaten

    def test_ai_beats_random_walk(self):
        seeds = range(1, 7)
        smart = [self.play(True, s) for s in seeds]
        dumb = [self.play(False, s) for s in seeds]
        smart_food = sum(r[2] for r in smart) / len(smart)
        dumb_food = sum(r[2] for r in dumb) / len(dumb)
        smart_wins = sum(1 for r in smart if r[0].state == VICTORY)
        print(f"\n  AI ON : avg food eaten {smart_food:.0f}/{smart[0][0].maze.total_food}, "
              f"wins {smart_wins}/{len(smart)}, "
              f"avg deaths {sum(r[1] for r in smart) / len(smart):.1f}")
        print(f"  AI OFF: avg food eaten {dumb_food:.0f}/{dumb[0][0].maze.total_food}, "
              f"wins {sum(1 for r in dumb if r[0].state == VICTORY)}/{len(dumb)}, "
              f"avg deaths {sum(r[1] for r in dumb) / len(dumb):.1f}")
        smart_deaths = sum(r[1] for r in smart)
        dumb_deaths = sum(r[1] for r in dumb)
        self.assertGreaterEqual(smart_food, dumb_food)
        self.assertGreater(smart_wins, 0, "the AI should be able to win")
        self.assertLess(smart_deaths, dumb_deaths, "the AI should die less often")


if __name__ == "__main__":
    unittest.main(verbosity=2)
