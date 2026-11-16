"""
game.py - The Game class: ties maze, Pac-Man, ghosts, AI and interface together.

Main parts of this file
    Game.__init__     create maze, characters, AI and the buttons
    Game.update       the "rules": movement, eating, collisions, lives, winning
    Game.draw         everything you see (maze, characters, AI overlays, panel)
    Game.run          the main loop: events -> update -> draw, 60 times a second
"""

import math
import random
import pygame

import ui
from ui import draw_text
from maze import Maze, TILE
from pacman import PacMan
from ghost import Ghost, WAITING, CHASE, FRIGHTENED, EATEN, BEHAVIOR_TEXT
from ai_controller import PacmanAI

# ---- Window layout -----------------------------------------------------------
MAZE_X, MAZE_Y = 20, 56
WINDOW_SIZE = (880, 664)
PANEL_X, PANEL_W = 592, 268
FPS = 60

# ---- Game rules --------------------------------------------------------------
START_LIVES = 3
POWER_TIME = 7.0          # seconds ghosts stay frightened
READY_TIME = 1.6
DEATH_TIME = 1.4
SPEED_STEPS = [0.5, 1.0, 1.5, 2.0, 3.0]

# ---- Game states -------------------------------------------------------------
MENU, PLAYING, PAUSED, GAME_OVER, VICTORY = "menu", "playing", "paused", "gameover", "victory"

GHOST_COLORS = {
    "Blinky": (255, 70, 70),
    "Pinky": (255, 150, 220),
    "Inky": (60, 220, 255),
    "Clyde": (255, 170, 50),
}
RELEASE_TIMES = {"Blinky": 0.0, "Pinky": 2.0, "Inky": 5.0, "Clyde": 8.0}


class Game:
    def __init__(self, screen, seed=None):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.rng = random.Random(seed)

        # Fonts
        self.f_small = ui.make_font(14)
        self.f_med = ui.make_font(17)
        self.f_bold = ui.make_font(17, bold=True)
        self.f_big = ui.make_font(30, bold=True)
        self.f_huge = ui.make_font(54, bold=True)

        # World
        self.maze = Maze()
        self.pac = PacMan(self.maze.pac_start)
        self.ghosts = [
            Ghost(name, self.maze.ghost_starts[name], GHOST_COLORS[name],
                  RELEASE_TIMES[name], random.Random(self.rng.random()))
            for name in ("Blinky", "Pinky", "Inky", "Clyde")
        ]
        self.ai = PacmanAI(self.maze, random.Random(self.rng.random()))

        # Settings the buttons control
        self.ai_on = True            # smart AI (A*/BFS) or random movement
        self.auto_mode = True        # True: AI drives Pac-Man, False: keyboard
        self.show_paths = True
        self.speed_index = 1

        # Game state
        self.state = MENU
        self.phase = "ready"         # ready / running / dying (inside PLAYING)
        self.phase_timer = 0.0
        self.score = 0
        self.lives = START_LIVES
        self.power_left = 0.0
        self.ghost_chain = 0
        self.popups = []             # floating "+200" texts: [text, (x, y), timer]
        self.anim_time = 0.0

        self.wall_surface = self._render_walls()
        self.overlay = pygame.Surface(
            (self.maze.width * TILE, self.maze.height * TILE), pygame.SRCALPHA)
        self._build_buttons()

    # ====================================================================
    # Buttons and settings
    # ====================================================================
    def _build_buttons(self):
        x, w, f = PANEL_X + 12, PANEL_W - 24, self.f_med
        half = (w - 8) // 2
        playing = lambda: self.state in (PLAYING, PAUSED)
        self.buttons = [
            ui.Button((x, 68, w, 36), "Start Game", self.start_new_game, f),
            ui.Button((x, 112, half, 36),
                      lambda: "Resume" if self.state == PAUSED else "Pause",
                      self.toggle_pause, f, enabled_fn=playing),
            ui.Button((x + half + 8, 112, half, 36), "Restart", self.start_new_game, f,
                      enabled_fn=lambda: self.state != MENU),
            ui.Button((x, 156, half, 36),
                      lambda: "AI: ON" if self.ai_on else "AI: OFF",
                      self.toggle_ai, f, state_fn=lambda: self.ai_on),
            ui.Button((x + half + 8, 156, half, 36),
                      lambda: "Mode: AUTO" if self.auto_mode else "Mode: MANUAL",
                      self.toggle_mode, f),
            ui.Button((x, 200, w, 36),
                      lambda: "Path view: ON" if self.show_paths else "Path view: OFF",
                      self.toggle_paths, f, state_fn=lambda: self.show_paths),
            ui.Button((x, 244, 44, 36), "-", lambda: self.change_speed(-1), self.f_bold),
            ui.Button((x + w - 44, 244, 44, 36), "+", lambda: self.change_speed(+1), self.f_bold),
        ]

    def toggle_pause(self):
        if self.state == PLAYING:
            self.state = PAUSED
        elif self.state == PAUSED:
            self.state = PLAYING

    def toggle_ai(self):
        self.ai_on = not self.ai_on
        self.ai.clear()

    def toggle_mode(self):
        self.auto_mode = not self.auto_mode
        self.ai.clear()
        self.pac.desired = (0, 0)

    def toggle_paths(self):
        self.show_paths = not self.show_paths

    def change_speed(self, delta):
        self.speed_index = max(0, min(len(SPEED_STEPS) - 1, self.speed_index + delta))

    # ====================================================================
    # Game flow
    # ====================================================================
    def start_new_game(self):
        self.maze.reset_food()
        self.score = 0
        self.lives = START_LIVES
        self.popups = []
        self._reset_positions()
        self.state = PLAYING

    def _reset_positions(self):
        self.pac.reset()
        for g in self.ghosts:
            g.reset()
        self.power_left = 0.0
        self.ghost_chain = 0
        self.ai.clear()
        self.phase = "ready"
        self.phase_timer = READY_TIME

    def _start_death(self):
        self.phase = "dying"
        self.phase_timer = DEATH_TIME

    def _finish_death(self):
        self.lives -= 1
        if self.lives <= 0:
            self.state = GAME_OVER
        else:
            self._reset_positions()

    # ====================================================================
    # UPDATE (the rules of the game)
    # ====================================================================
    def update(self, dt_real):
        self.anim_time += dt_real
        for p in self.popups:
            p[2] -= dt_real
        self.popups = [p for p in self.popups if p[2] > 0]
        if self.state != PLAYING:
            return

        # Cap dt so a lag spike can never make characters jump through walls
        dt = min(dt_real, 0.05) * SPEED_STEPS[self.speed_index]

        if self.phase == "ready":
            self.phase_timer -= dt
            if self.phase_timer <= 0:
                self.phase = "running"
            return
        if self.phase == "dying":
            self.phase_timer -= dt
            if self.phase_timer <= 0:
                self._finish_death()
            return

        self._update_pacman(dt)
        for g in self.ghosts:
            g.update(dt, self.maze, self.pac, self.ghosts[0], self.ai_on)
        self._check_eating()
        self._check_collisions()
        self._update_power(dt)
        if self.phase == "running" and self.maze.food_left == 0:
            self.state = VICTORY

    def _update_pacman(self, dt):
        pac = self.pac
        if not self.auto_mode:                       # keyboard
            self.ai.clear()
            self.ai.status = "MANUAL - arrow keys"
            chooser = lambda: pac.manual_choice(self.maze)
        elif not self.ai_on:                         # random wandering
            chooser = lambda: self.ai.random_step(pac)
        else:                                        # A* brain
            if pac.next_tile is not None and pac.progress < 0.5:
                # Early in a step: if danger appeared, turn around immediately
                nxt = self.ai.decide(pac, self.ghosts, self.power_left)
                if self.ai.threat and nxt is not None and nxt != pac.next_tile:
                    pac.reverse()
            chooser = lambda: self.ai.decide(pac, self.ghosts, self.power_left)
        pac.update(dt, chooser)

    def _check_eating(self):
        tile = self.pac.current_tile
        if tile in self.maze.dots:
            self.maze.dots.discard(tile)
            self.score += 10
        elif tile in self.maze.pellets:
            self.maze.pellets.discard(tile)
            self.score += 50
            self.power_left = POWER_TIME
            self.ghost_chain = 0
            for g in self.ghosts:
                if g.state == CHASE:
                    g.state = FRIGHTENED

    def _check_collisions(self):
        px, py = self.pac.pos
        for g in self.ghosts:
            if g.state in (WAITING, EATEN):
                continue
            gx, gy = g.pos
            if math.hypot(px - gx, py - gy) < 0.6:
                if g.state == FRIGHTENED:
                    g.state = EATEN
                    points = 200 * (2 ** self.ghost_chain)
                    self.ghost_chain = min(self.ghost_chain + 1, 3)
                    self.score += points
                    self.popups.append([f"+{points}", self._center(gx, gy), 1.0])
                elif g.state == CHASE:
                    self._start_death()
                    return

    def _update_power(self, dt):
        if self.power_left > 0:
            self.power_left -= dt
            if self.power_left <= 0:
                self.power_left = 0.0
                for g in self.ghosts:
                    if g.state == FRIGHTENED:
                        g.state = CHASE

    # ====================================================================
    # Events
    # ====================================================================
    def handle_event(self, event):
        # ---- touch / swipe support (phone) ----
        if event.type == pygame.MOUSEBUTTONDOWN:
            self._touch_start = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and getattr(self, "_touch_start", None):
            sx, sy = self._touch_start
            self._touch_start = None
            dx, dy = event.pos[0] - sx, event.pos[1] - sy
            if max(abs(dx), abs(dy)) >= 40 and self.state == PLAYING and not self.auto_mode:
                if abs(dx) > abs(dy):
                    self.pac.request_direction((1 if dx > 0 else -1, 0))
                else:
                    self.pac.request_direction((0, 1 if dy > 0 else -1))
                return
            if self.state in (MENU, GAME_OVER, VICTORY) and \
                    not any(b.rect.collidepoint(event.pos) for b in self.buttons):
                self.start_new_game()
                return
        for b in self.buttons:
            if b.handle_event(event):
                return
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        dirs = {pygame.K_UP: (0, -1), pygame.K_w: (0, -1),
                pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1),
                pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0),
                pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0)}
        if k in dirs and self.state == PLAYING and not self.auto_mode:
            self.pac.request_direction(dirs[k])
        elif k == pygame.K_SPACE:
            self.toggle_pause()
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.state in (MENU, GAME_OVER, VICTORY):
            self.start_new_game()
        elif k == pygame.K_r and self.state != MENU:
            self.start_new_game()
        elif k == pygame.K_i:
            self.toggle_ai()
        elif k == pygame.K_m:
            self.toggle_mode()
        elif k == pygame.K_v:
            self.toggle_paths()
        elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.change_speed(+1)
        elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.change_speed(-1)

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (
                        event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
                else:
                    self.handle_event(event)
            self.update(dt)
            self.draw()
            pygame.display.flip()

    # ====================================================================
    # DRAWING
    # ====================================================================
    def _center(self, col, row):
        """Pixel centre of a (possibly fractional) tile position."""
        return (MAZE_X + (col + 0.5) * TILE, MAZE_Y + (row + 0.5) * TILE)

    def _render_walls(self):
        """Draw the maze walls once into a surface (much faster than every frame)."""
        m = self.maze
        surf = pygame.Surface((m.width * TILE, m.height * TILE))
        surf.fill(ui.BG)
        for (c, r) in m.walls:
            x, y = c * TILE, r * TILE
            pygame.draw.rect(surf, ui.WALL_FILL, (x, y, TILE, TILE))
            for dx, dy, p1, p2 in (
                    (0, -1, (x + 2, y + 2), (x + TILE - 3, y + 2)),
                    (0, 1, (x + 2, y + TILE - 3), (x + TILE - 3, y + TILE - 3)),
                    (-1, 0, (x + 2, y + 2), (x + 2, y + TILE - 3)),
                    (1, 0, (x + TILE - 3, y + 2), (x + TILE - 3, y + TILE - 3))):
                n = (c + dx, r + dy)
                if m.in_bounds(n) and n not in m.walls:   # edge facing a corridor
                    pygame.draw.line(surf, ui.WALL_EDGE, p1, p2, 2)
        for (c, r) in m.doors:
            pygame.draw.rect(surf, ui.DOOR, (c * TILE + 2, r * TILE + TILE // 2 - 2, TILE - 4, 4))
        return surf

    def draw(self):
        s = self.screen
        s.fill(ui.BG)
        self._draw_top_bar()
        s.blit(self.wall_surface, (MAZE_X, MAZE_Y))
        self._draw_food()
        if self.show_paths and self.state in (PLAYING, PAUSED) and self.phase == "running":
            self._draw_ai_overlay()
        for g in self.ghosts:
            self._draw_ghost(g)
        self._draw_pacman()
        for text, pos, t in self.popups:
            draw_text(s, text, self.f_bold, ui.ACCENT, (pos[0], pos[1] - (1 - t) * 20), center=True)
        self._draw_state_overlays()
        self._draw_panel()

    # ---- top bar --------------------------------------------------------
    def _draw_top_bar(self):
        s = self.screen
        draw_text(s, "SCORE", self.f_small, ui.TEXT_DIM, (MAZE_X, 4))
        draw_text(s, f"{self.score:06d}", self.f_big, ui.ACCENT, (MAZE_X, 18))
        draw_text(s, "LIVES", self.f_small, ui.TEXT_DIM, (MAZE_X + 200, 4))
        for i in range(max(self.lives, 0)):
            self._pac_shape((MAZE_X + 212 + i * 30, 36), 10, (1, 0), 0.5)
        if self.power_left > 0:
            draw_text(s, f"POWER {self.power_left:3.1f}s", self.f_bold, (90, 140, 255),
                      (MAZE_X + 330, 20))
        draw_text(s, "SMART PAC-MAN AI", self.f_bold, ui.TEXT, (PANEL_X + 12, 12))
        draw_text(s, "A* for Pac-Man  |  BFS for ghosts", self.f_small, ui.TEXT_DIM,
                  (PANEL_X + 12, 32))

    # ---- food -----------------------------------------------------------
    def _draw_food(self):
        for (c, r) in self.maze.dots:
            pygame.draw.circle(self.screen, ui.DOT, self._center(c, r), 3)
        pulse = 6 + 2 * math.sin(self.anim_time * 6)
        for (c, r) in self.maze.pellets:
            pygame.draw.circle(self.screen, ui.DOT, self._center(c, r), int(pulse))

    # ---- AI overlays (the visual demonstration) ---------------------------
    def _draw_ai_overlay(self):
        ov = self.overlay
        ov.fill((0, 0, 0, 0))
        # Red: dangerous tiles (the redder, the closer to a ghost)
        for (c, r), lvl in self.ai.danger_tiles.items():
            pygame.draw.rect(ov, (255, 40, 40, 35 + lvl * 28),
                             (c * TILE + 1, r * TILE + 1, TILE - 2, TILE - 2), border_radius=5)
        self.screen.blit(ov, (MAZE_X, MAZE_Y))

        # Ghost paths (BFS): one colour per ghost
        for g in self.ghosts:
            if len(g.path) > 1 and g.state in (CHASE, EATEN):
                pts = [self._center(*g.pos)] + [self._center(c, r) for c, r in g.path[1:]]
                pygame.draw.lines(self.screen, g.color, False, pts, 2)
                pygame.draw.circle(self.screen, g.color, pts[-1], 5, 2)

        # Pac-Man's planned path (A*) in green
        ai = self.ai
        if self.auto_mode and self.ai_on and len(ai.path) > 1:
            pts = [self._center(*self.pac.pos)] + [self._center(c, r) for c, r in ai.path[1:]]
            pygame.draw.lines(self.screen, ui.GREEN, False, pts, 4)
            for p in pts[1:]:
                pygame.draw.circle(self.screen, ui.GREEN, p, 4)
        if self.auto_mode and self.ai_on and ai.target is not None:
            ring = 11 + 2 * math.sin(self.anim_time * 8)
            pygame.draw.circle(self.screen, (255, 255, 255), self._center(*ai.target), int(ring), 2)

    # ---- characters -------------------------------------------------------
    def _pac_shape(self, center, radius, direction, mouth):
        """Draw a Pac-Man pie shape. mouth = 0..1 (how wide the mouth is open)."""
        cx, cy = center
        angle = math.atan2(direction[1], direction[0]) if direction != (0, 0) else 0.0
        half = 0.05 + mouth * 0.7
        pts = [(cx, cy)]
        a0, a1 = angle + half, angle + 2 * math.pi - half
        for i in range(25):
            a = a0 + (a1 - a0) * i / 24
            pts.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
        pygame.draw.polygon(self.screen, ui.ACCENT, pts)

    def _draw_pacman(self):
        pac = self.pac
        center = self._center(*pac.pos)
        r = TILE * 0.46
        if self.phase == "dying" and self.state in (PLAYING, PAUSED):
            t = 1 - max(self.phase_timer, 0) / DEATH_TIME
            if t < 0.97:
                self._pac_shape(center, r * (1 - 0.3 * t), (0, -1), 0.05 + t * 4.2)
            return
        moving = pac.next_tile is not None and self.state == PLAYING
        mouth = abs(math.sin(self.anim_time * 11)) if moving else 0.35
        self._pac_shape(center, r, pac.direction, mouth)

    def _draw_ghost(self, g):
        s = self.screen
        cx, cy = self._center(*g.pos)
        r = TILE * 0.46
        if g.state != EATEN:
            if g.state == FRIGHTENED:
                flash = self.power_left < 2.0 and int(self.anim_time * 6) % 2 == 0
                body = (240, 240, 255) if flash else (40, 60, 220)
            else:
                body = g.color
            bob = 0 if g.state != WAITING else math.sin(self.anim_time * 6) * 2
            cy += bob
            wave = int(self.anim_time * 8) % 2
            pygame.draw.circle(s, body, (cx, cy - r * 0.1), r)
            pts = [(cx - r, cy - r * 0.1), (cx - r, cy + r)]
            for i in range(1, 7):
                x = cx - r + i * (2 * r / 6)
                low = (i % 2 == wave)
                pts.append((x, cy + r if low else cy + r * 0.65))
            pts.append((cx + r, cy - r * 0.1))
            pygame.draw.polygon(s, body, pts)
        # Eyes
        if g.state == FRIGHTENED:
            for sx in (-0.35, 0.35):
                pygame.draw.circle(s, (255, 230, 200), (cx + sx * r, cy - r * 0.25), 3)
            zig = [(cx + (i - 3) * r * 0.28, cy + r * (0.35 if i % 2 else 0.5)) for i in range(7)]
            pygame.draw.lines(s, (255, 230, 200), False, zig, 2)
        else:
            d = g.direction
            for sx in (-0.4, 0.4):
                ex, ey = cx + sx * r, cy - r * 0.2
                pygame.draw.circle(s, (255, 255, 255), (ex, ey), r * 0.3)
                pygame.draw.circle(s, (20, 30, 150), (ex + d[0] * 2.5, ey + d[1] * 2.5), r * 0.15)

    # ---- overlays: menu / game over / victory ------------------------------
    def _draw_state_overlays(self):
        mw, mh = self.maze.width * TILE, self.maze.height * TILE
        center = (MAZE_X + mw // 2, MAZE_Y + mh // 2)
        if self.state == PLAYING and self.phase == "ready":
            draw_text(self.screen, "READY!", self.f_big, ui.ACCENT,
                      self._center(9, 11.4), center=True)
        if self.state == MENU:
            self._dim_maze()
            draw_text(self.screen, "SMART PAC-MAN", self.f_huge, ui.ACCENT,
                      (center[0], center[1] - 110), center=True)
            draw_text(self.screen, "Artificial Intelligence with A* and BFS", self.f_med,
                      ui.TEXT, (center[0], center[1] - 60), center=True)
            for i, line in enumerate([
                    "Click  Start Game  or press ENTER",
                    "AUTO mode: Pac-Man plays by itself (A*)",
                    "MANUAL mode: arrow keys / WASD",
                    "SPACE pause   R restart   I AI   M mode   V paths   +/- speed"]):
                draw_text(self.screen, line, self.f_small, ui.TEXT_DIM,
                          (center[0], center[1] - 5 + i * 24), center=True)
        elif self.state == PAUSED:
            self._dim_maze()
            draw_text(self.screen, "PAUSED", self.f_huge, ui.TEXT, center, center=True)
        elif self.state == GAME_OVER:
            self._dim_maze()
            draw_text(self.screen, "GAME OVER", self.f_huge, ui.RED,
                      (center[0], center[1] - 30), center=True)
            draw_text(self.screen, f"Final score: {self.score}", self.f_big, ui.TEXT,
                      (center[0], center[1] + 30), center=True)
            draw_text(self.screen, "Press R / ENTER or click Restart", self.f_small,
                      ui.TEXT_DIM, (center[0], center[1] + 70), center=True)
        elif self.state == VICTORY:
            self._dim_maze()
            draw_text(self.screen, "YOU WIN!", self.f_huge, ui.GREEN,
                      (center[0], center[1] - 30), center=True)
            draw_text(self.screen, f"Final score: {self.score}", self.f_big, ui.TEXT,
                      (center[0], center[1] + 30), center=True)
            draw_text(self.screen, "Press R / ENTER or click Restart", self.f_small,
                      ui.TEXT_DIM, (center[0], center[1] + 70), center=True)

    def _dim_maze(self):
        veil = pygame.Surface((self.maze.width * TILE, self.maze.height * TILE), pygame.SRCALPHA)
        veil.fill((8, 10, 18, 200))
        self.screen.blit(veil, (MAZE_X, MAZE_Y))

    # ---- right-hand panel ----------------------------------------------------
    def _draw_panel(self):
        s = self.screen
        mouse = pygame.mouse.get_pos()
        for b in self.buttons:
            b.draw(s, mouse)
        x, w = PANEL_X + 12, PANEL_W - 24
        draw_text(s, f"Speed {SPEED_STEPS[self.speed_index]:.1f}x", self.f_med, ui.TEXT,
                  (x + w // 2, 262), center=True)

        # AI status box
        box = pygame.Rect(PANEL_X, 292, PANEL_W, MAZE_Y + self.maze.height * TILE - 292)
        pygame.draw.rect(s, ui.PANEL, box, border_radius=10)
        pygame.draw.rect(s, ui.PANEL_BORDER, box, width=1, border_radius=10)
        draw_text(s, "AI STATUS", self.f_bold, ui.ACCENT, (x, 300))

        ai = self.ai
        if not self.auto_mode:
            mode, status, algo, target = "MANUAL (keyboard)", "You are driving", "-", "-"
        elif not self.ai_on:
            mode, status, algo, target = "AUTO, AI OFF", "Random walk", "None", "-"
        else:
            mode = "AUTOMATIC (AI)"
            status = ai.status if self.state != MENU else "Idle"
            algo, target = ai.algorithm, ai.target_label
        if self.state == PAUSED:
            status = "Paused"
        route = len(ai.path) - 1 if (self.auto_mode and self.ai_on and ai.path) else 0
        rows = [("Mode", mode), ("Status", status), ("Algorithm", algo), ("Target", target),
                ("Route", f"{max(route, 0)} step" + ("" if route == 1 else "s")),
                ("Danger", f"{len(ai.danger_tiles) if self.ai_on else 0} red tiles")]
        status_color = ui.RED if "FLEEING" in status or "danger" in status else ui.GREEN
        y = 326
        for label, value in rows:
            draw_text(s, label, self.f_small, ui.TEXT_DIM, (x, y + 2))
            color = status_color if label == "Status" else ui.TEXT
            draw_text(s, value, self.f_small, color, (x + 70, y + 2), max_width=w - 70)
            y += 22

        y += 8
        pygame.draw.line(s, ui.PANEL_BORDER, (x, y), (x + w, y))
        draw_text(s, "GHOSTS  (BFS chasers)", self.f_bold, ui.ACCENT, (x, y + 6))
        y += 32
        for g in self.ghosts:
            pygame.draw.circle(s, g.color, (x + 6, y + 9), 6)
            draw_text(s, g.name, self.f_small, ui.TEXT, (x + 18, y + 2))
            if not self.ai_on:
                desc = "random wander"
            elif g.state == CHASE:
                desc = BEHAVIOR_TEXT[g.name]
            else:
                desc = {WAITING: "waiting in house", FRIGHTENED: "frightened",
                        EATEN: "BFS back home"}[g.state]
            draw_text(s, desc, self.f_small, ui.TEXT_DIM, (x + 76, y + 2), max_width=w - 76)
            y += 22

        y += 8
        pygame.draw.line(s, ui.PANEL_BORDER, (x, y), (x + w, y))
        legend = [(ui.GREEN, "A* path"), (ui.RED, "Danger tiles"),
                  ((255, 255, 255), "Target"), ((255, 170, 50), "Ghost paths")]
        for i, (color, text) in enumerate(legend):
            lx = x + (i % 2) * (w // 2)
            ly = y + 10 + (i // 2) * 22
            pygame.draw.rect(s, color, (lx, ly + 3, 12, 12), border_radius=3)
            draw_text(s, text, self.f_small, ui.TEXT_DIM, (lx + 18, ly), max_width=w // 2 - 20)
