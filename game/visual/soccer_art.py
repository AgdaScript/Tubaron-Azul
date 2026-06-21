from __future__ import annotations
import pygame
from engine.resources.asset_manager import AssetManager

"""Builds the per-team player sprites from the three base poses.

There is one base outfield pose (Cape Verde blue kit), one kicking pose, and one
diving keeper. Every other nation is produced by recolouring the kit: the blue
shirt is hue-swapped to the team's shirt colour and the yellow keeper to the
team's keeper colour. The base renders are Cape Verde players, so for every other
nation the brown skin is also relit to a lighter tone to match those squads. Each
set is built once and cached.
"""

Color = tuple[int, int, int]

PLAYER_HEIGHT = 70
KEEPER_HEIGHT = 56
DIVE_HEIGHT = 60
RUN_FRAME_COUNT = 8

# Pale skin target for non-Cape-Verde squads, relit per pixel to keep shading.
LIGHT_SKIN = (236, 198, 172)


class TeamSprites:
    def __init__(self, idle: pygame.Surface, kick: pygame.Surface,
                 keeper_idle: pygame.Surface, keeper_dive: pygame.Surface,
                 run_frames: list[pygame.Surface], keeper_run_frames: list[pygame.Surface]) -> None:
        self.idle_right = idle
        self.idle_left = pygame.transform.flip(idle, True, False)
        self.kick_right = kick
        self.kick_left = pygame.transform.flip(kick, True, False)
        self.keeper_idle_right = keeper_idle
        self.keeper_idle_left = pygame.transform.flip(keeper_idle, True, False)
        self.keeper_dive_right = keeper_dive
        self.keeper_dive_left = pygame.transform.flip(keeper_dive, True, False)
        self.run_right = run_frames
        self.run_left = [pygame.transform.flip(frame, True, False) for frame in run_frames]
        self.keeper_run_right = keeper_run_frames
        self.keeper_run_left = [pygame.transform.flip(frame, True, False) for frame in keeper_run_frames]


def _IsShirtBlue(r: int, g: int, b: int) -> bool:
    return b > r + 24 and b > g + 16 and b > 70


def _IsKeeperYellow(r: int, g: int, b: int) -> bool:
    return r > 140 and g > 110 and b < 130 and (r + g) > 2.2 * b


def _IsSkin(r: int, g: int, b: int) -> bool:
    # Warm brown skin: red roughly twice green, clearly above blue. The ratio
    # keeps the keeper's yellow (red only ~1.3x green) out of the mask.
    return 45 < r < 190 and r > g * 1.6 and g > b + 6 and b < 80


def _RecolorSkin(surface: pygame.Surface) -> pygame.Surface:
    """Relights the brown base skin to a lighter tone, keeping its shading."""
    out = surface.copy()
    width = out.get_width()
    height = out.get_height()
    out.lock()

    for y in range(height):
        for x in range(width):
            r, g, b, a = out.get_at((x, y))

            if a == 0 or not _IsSkin(r, g, b):
                continue

            lum = (0.3 * r + 0.59 * g + 0.11 * b) / 255.0
            factor = min(1.28, max(0.5, lum * 2.2 + 0.34))
            out.set_at((x, y), (
                min(255, int(LIGHT_SKIN[0] * factor)),
                min(255, int(LIGHT_SKIN[1] * factor)),
                min(255, int(LIGHT_SKIN[2] * factor)),
                a,
            ))

    out.unlock()
    return out


def _RecolorMask(surface: pygame.Surface, matches, target: Color) -> pygame.Surface:
    """Replaces masked pixels with target colour, keeping their original shading."""
    out = surface.copy()
    width = out.get_width()
    height = out.get_height()
    out.lock()

    for y in range(height):
        for x in range(width):
            r, g, b, a = out.get_at((x, y))

            if a == 0 or not matches(r, g, b):
                continue

            lum = (0.3 * r + 0.59 * g + 0.11 * b) / 255.0
            factor = min(1.12, max(0.28, lum * 1.18))
            new = (
                min(255, int(target[0] * factor)),
                min(255, int(target[1] * factor)),
                min(255, int(target[2] * factor)),
                a,
            )
            out.set_at((x, y), new)

    out.unlock()
    return out


def _ScaleToHeight(surface: pygame.Surface, target_h: int) -> pygame.Surface:
    scale = target_h / surface.get_height()
    size = (max(1, int(surface.get_width() * scale)), target_h)
    return pygame.transform.smoothscale(surface, size)


def _TrimRight(surface: pygame.Surface, keep_ratio: float) -> pygame.Surface:
    width = int(surface.get_width() * keep_ratio)
    return surface.subsurface(pygame.Rect(0, 0, width, surface.get_height())).copy()


class SpriteFactory:
    """Loads the base art once and serves recoloured, scaled team sprite sets."""

    def __init__(self, assets: AssetManager) -> None:
        base_idle = assets.LoadImage("players/outfield_idle.png")
        base_kick = _TrimRight(assets.LoadImage("players/outfield_kick.png"), 0.82)
        base_keeper = assets.LoadImage("players/keeper.png")
        self._idle = _ScaleToHeight(base_idle, PLAYER_HEIGHT)
        self._kick = _ScaleToHeight(base_kick, PLAYER_HEIGHT)
        self._keeper_dive = _ScaleToHeight(base_keeper, DIVE_HEIGHT)
        self._keeper_stand_src = _ScaleToHeight(base_idle, KEEPER_HEIGHT)
        self._keeper_run_src = [
            _ScaleToHeight(assets.LoadImage(f"player_run_frames/{index}.png"), KEEPER_HEIGHT)
            for index in range(1, RUN_FRAME_COUNT + 1)
        ]
        self._run_frames = [
            _ScaleToHeight(assets.LoadImage(f"player_run_frames/{index}.png"), PLAYER_HEIGHT)
            for index in range(1, RUN_FRAME_COUNT + 1)
        ]
        self._cache: dict[str, TeamSprites] = {}

    def GetTeamSprites(self, team_id: str, shirt: Color, keeper: Color) -> TeamSprites:
        if team_id in self._cache:
            return self._cache[team_id]

        idle = _RecolorMask(self._idle, _IsShirtBlue, shirt)
        kick = _RecolorMask(self._kick, _IsShirtBlue, shirt)
        keeper_idle = _RecolorMask(self._keeper_stand_src, _IsShirtBlue, keeper)
        keeper_dive = _RecolorMask(self._keeper_dive, _IsKeeperYellow, keeper)
        run_frames = [_RecolorMask(frame, _IsShirtBlue, shirt) for frame in self._run_frames]
        keeper_run_frames = [_RecolorMask(frame, _IsShirtBlue, keeper) for frame in self._keeper_run_src]

        if team_id != "capeverde":
            idle = _RecolorSkin(idle)
            kick = _RecolorSkin(kick)
            keeper_idle = _RecolorSkin(keeper_idle)
            keeper_dive = _RecolorSkin(keeper_dive)
            run_frames = [_RecolorSkin(frame) for frame in run_frames]
            keeper_run_frames = [_RecolorSkin(frame) for frame in keeper_run_frames]

        sprites = TeamSprites(idle, kick, keeper_idle, keeper_dive, run_frames, keeper_run_frames)
        self._cache[team_id] = sprites
        return sprites
