from __future__ import annotations
import pygame
from engine.rendering.draw import DrawSlantedPanel
from engine.audio.audio_manager import AudioManager
from game.data import theme

MUTE_SIZE = 44
MUTE_MARGIN = 14

_icon_cache: dict[tuple[bool, bool], pygame.Surface] = {}


def GetMuteRect() -> pygame.Rect:
    return pygame.Rect(
        theme.SCREEN_WIDTH - MUTE_SIZE - MUTE_MARGIN,
        MUTE_MARGIN,
        MUTE_SIZE,
        MUTE_SIZE,
    )


def HandleMuteInput(event: pygame.event.Event, audio: AudioManager, *, allow_key: bool = True) -> bool:
    if not audio.IsEnabled():
        return False

    if allow_key and event.type == pygame.KEYDOWN and event.key == pygame.K_m:
        audio.ToggleMute()
        return True

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        if GetMuteRect().collidepoint(event.pos):
            audio.ToggleMute()
            return True

    return False


def DrawMuteControl(surface: pygame.Surface, audio: AudioManager) -> None:
    rect = GetMuteRect()
    muted = audio.IsMuted()
    enabled = audio.IsEnabled()

    if not enabled:
        DrawSlantedPanel(surface, rect, (*theme.CV_BLUE_DEEP, 170), theme.GREY, 10, 2)
        icon_color = theme.GREY
    elif muted:
        DrawSlantedPanel(surface, rect, (*theme.CV_RED, 220), theme.CV_WHITE, 10, 2)
        icon_color = theme.CV_WHITE
    else:
        DrawSlantedPanel(surface, rect, (*theme.CV_BLUE_DEEP, 215), theme.CV_WHITE, 10, 2)
        icon_color = theme.CV_WHITE

    icon = _GetSpeakerIcon(muted=muted and enabled, disabled=not enabled)
    surface.blit(icon, (rect.centerx - icon.get_width() // 2, rect.centery - icon.get_height() // 2))


def _GetSpeakerIcon(*, muted: bool, disabled: bool) -> pygame.Surface:
    key = (muted, disabled)
    cached = _icon_cache.get(key)
    if cached is not None:
        return cached

    size = 28
    icon = pygame.Surface((size, size), pygame.SRCALPHA)
    color = theme.GREY if disabled else theme.CV_WHITE
    outline = theme.INK if not disabled else theme.DARK

    body = pygame.Rect(4, 10, 7, 8)
    pygame.draw.rect(icon, color, body)
    pygame.draw.rect(icon, outline, body, 1)

    cone = [(body.right, body.centery - 5), (body.right + 9, body.centery - 9), (body.right + 9, body.centery + 9), (body.right, body.centery + 5)]
    pygame.draw.polygon(icon, color, cone)
    pygame.draw.polygon(icon, outline, cone, 1)

    if not muted and not disabled:
        pygame.draw.arc(icon, color, pygame.Rect(16, 6, 10, 16), -0.9, 0.9, 2)
        pygame.draw.arc(icon, color, pygame.Rect(19, 3, 12, 22), -0.9, 0.9, 2)
    elif muted and not disabled:
        pygame.draw.line(icon, color, (17, 7), (25, 21), 3)
        pygame.draw.line(icon, outline, (17, 7), (25, 21), 1)

    _icon_cache[key] = icon
    return icon
