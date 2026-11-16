"""
main.py - Start the game.   Run with:   python main.py
"""

import sys


def main():
    try:
        import pygame
    except ImportError:
        print("Pygame is not installed. Run:  pip install -r requirements.txt")
        sys.exit(1)

    try:
        pygame.display.init()   # this game has no sound, so only the display
        pygame.font.init()      # and fonts are needed
        from game import Game, WINDOW_SIZE
        flags = pygame.SCALED | (pygame.FULLSCREEN if hasattr(sys, "getandroidapilevel") or "ANDROID_ARGUMENT" in __import__("os").environ else 0)
        screen = pygame.display.set_mode(WINDOW_SIZE, flags)   # SCALED fits any phone screen
        pygame.display.set_caption("Smart Pac-Man AI  -  A* and BFS")
        Game(screen).run()
    except pygame.error as err:
        print(f"Pygame could not start the display: {err}")
        sys.exit(1)
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
