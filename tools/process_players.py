from __future__ import annotations
import os
import sys
from collections import deque
import pygame

"""Turns the raw player photos (white background, one big pose each) into clean,
transparent, cropped game sprites.

The source art is a single pose per file on a flat white background. We key out
only the background-connected white by flood-filling inward from the borders, so
the white socks, shoelaces and the ball (all enclosed by darker outlines) survive
untouched. Then we trim to the silhouette and save at a workable resolution; the
game scales these down further at load time and recolours the kit per team.
"""

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(PROJECT_ROOT, "assets", "players")

# (source file, output name, target height before keying)
_SOURCES = [
    ("player.png", "outfield_idle.png", 460),
    ("player_kick.png", "outfield_kick.png", 460),
    ("vozinha.png", "keeper.png", 420),
    ("assets/players/keeper_free_hands.jpeg", "keeper_free_hands.png", 420),
]

_WHITE_CUT = 232
_FRINGE_CUT = 238


_BLACK_CUT = 32


def _IsBlack(color: tuple[int, int, int, int], cut: int) -> bool:
    return color[0] <= cut and color[1] <= cut and color[2] <= cut


def _KeyOutBlackBackground(surface: pygame.Surface) -> None:
    width = surface.get_width()
    height = surface.get_height()
    transparent = (0, 0, 0, 0)
    visited = [[False] * width for _ in range(height)]
    queue: deque[tuple[int, int]] = deque()

    for x in range(width):
        for y in (0, height - 1):
            queue.append((x, y))

    for y in range(height):
        for x in (0, width - 1):
            queue.append((x, y))

    while queue:
        x, y = queue.popleft()

        if x < 0 or y < 0 or x >= width or y >= height or visited[y][x]:
            continue

        visited[y][x] = True

        if not _IsBlack(surface.get_at((x, y)), _BLACK_CUT):
            continue

        surface.set_at((x, y), transparent)
        queue.append((x + 1, y))
        queue.append((x - 1, y))
        queue.append((x, y + 1))
        queue.append((x, y - 1))


def _IsWhite(color: tuple[int, int, int, int], cut: int) -> bool:
    return color[0] >= cut and color[1] >= cut and color[2] >= cut


def _KeyOutBackground(surface: pygame.Surface) -> None:
    width = surface.get_width()
    height = surface.get_height()
    transparent = (0, 0, 0, 0)
    visited = [[False] * width for _ in range(height)]
    queue: deque[tuple[int, int]] = deque()

    for x in range(width):
        for y in (0, height - 1):
            queue.append((x, y))

    for y in range(height):
        for x in (0, width - 1):
            queue.append((x, y))

    while queue:
        x, y = queue.popleft()

        if x < 0 or y < 0 or x >= width or y >= height or visited[y][x]:
            continue

        visited[y][x] = True

        if not _IsWhite(surface.get_at((x, y)), _WHITE_CUT):
            continue

        surface.set_at((x, y), transparent)
        queue.append((x + 1, y))
        queue.append((x - 1, y))
        queue.append((x, y + 1))
        queue.append((x, y - 1))

    _RemoveFringe(surface, visited)


def _RemoveFringe(surface: pygame.Surface, visited: list[list[bool]]) -> None:
    """Drops the bright halo pixels left where antialiasing blended into white."""
    width = surface.get_width()
    height = surface.get_height()

    for y in range(height):
        for x in range(width):
            color = surface.get_at((x, y))

            if color[3] == 0 or not _IsWhite(color, _FRINGE_CUT):
                continue

            if _TouchesCleared(surface, x, y):
                surface.set_at((x, y), (0, 0, 0, 0))


def _TouchesCleared(surface: pygame.Surface, x: int, y: int) -> bool:
    width = surface.get_width()
    height = surface.get_height()

    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy

        if nx < 0 or ny < 0 or nx >= width or ny >= height:
            continue

        if surface.get_at((nx, ny))[3] == 0:
            return True

    return False


def _Autocrop(surface: pygame.Surface) -> pygame.Surface:
    rect = surface.get_bounding_rect(min_alpha=8)
    return surface.subsurface(rect).copy()


def _ScaleToHeight(surface: pygame.Surface, target_h: int) -> pygame.Surface:
    scale = target_h / surface.get_height()
    size = (max(1, int(surface.get_width() * scale)), target_h)
    return pygame.transform.scale(surface, size)


def ProcessAll() -> None:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((16, 16))
    os.makedirs(OUT_DIR, exist_ok=True)

    for source, out_name, target_h in _SOURCES:
        path = os.path.join(PROJECT_ROOT, source)
        raw = pygame.image.load(path).convert_alpha()
        work = _ScaleToHeight(raw, target_h)
        if source.endswith("keeper_free_hands.jpeg"):
            _KeyOutBlackBackground(work)
        else:
            _KeyOutBackground(work)
        cropped = _Autocrop(work)
        pygame.image.save(cropped, os.path.join(OUT_DIR, out_name))
        print(f"  {source} -> players/{out_name}  {cropped.get_size()}")


if __name__ == "__main__":
    ProcessAll()
    print("players processed")
    sys.exit(0)
