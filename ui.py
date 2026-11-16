"""
ui.py - Colours, fonts and the Button widget (the dark theme lives here).
"""

import pygame

# ---- Dark theme colours ----------------------------------------------------
BG = (12, 14, 22)
PANEL = (22, 26, 40)
PANEL_BORDER = (44, 52, 80)
TEXT = (230, 234, 245)
TEXT_DIM = (140, 150, 175)
ACCENT = (255, 214, 10)
WALL_FILL = (14, 20, 64)
WALL_EDGE = (52, 96, 255)
DOOR = (255, 150, 200)
DOT = (255, 224, 180)
GREEN = (0, 230, 120)
RED = (255, 60, 60)
BTN = (36, 42, 66)
BTN_HOVER = (52, 62, 98)
BTN_ON = (24, 120, 80)
BTN_OFF = (120, 40, 50)
BTN_DISABLED = (28, 32, 48)


def make_font(size, bold=False):
    """Load a nice system font; fall back to pygame's default if missing."""
    try:
        return pygame.font.SysFont("segoeui,helvetica,arial,dejavusans", size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size + 6)


def draw_text(surface, text, font, color, pos, center=False, max_width=None):
    """Draw text; shorten it with '...' if it would be wider than max_width."""
    if max_width is not None:
        while font.size(text)[0] > max_width and len(text) > 3:
            text = text[:-4] + "..."
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    surface.blit(img, rect)
    return rect


class Button:
    """A clickable rectangle. `label` may be a string or a function returning one."""

    def __init__(self, rect, label, callback, font, state_fn=None, enabled_fn=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.callback = callback
        self.font = font
        self.state_fn = state_fn        # returns True/False -> green/red tint, None -> normal
        self.enabled_fn = enabled_fn    # returns False -> greyed out

    def enabled(self):
        return self.enabled_fn() if self.enabled_fn else True

    def handle_event(self, event):
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.rect.collidepoint(event.pos) and self.enabled()):
            self.callback()
            return True
        return False

    def draw(self, surface, mouse_pos):
        text = self.label() if callable(self.label) else self.label
        if not self.enabled():
            color, text_color = BTN_DISABLED, (80, 88, 110)
        else:
            state = self.state_fn() if self.state_fn else None
            hover = self.rect.collidepoint(mouse_pos)
            if state is True:
                color = tuple(min(255, c + 25) for c in BTN_ON) if hover else BTN_ON
            elif state is False:
                color = tuple(min(255, c + 25) for c in BTN_OFF) if hover else BTN_OFF
            else:
                color = BTN_HOVER if hover else BTN
            text_color = TEXT
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, PANEL_BORDER, self.rect, width=1, border_radius=8)
        draw_text(surface, text, self.font, text_color, self.rect.center, center=True)
