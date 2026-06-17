from __future__ import annotations
import pygame

Color = tuple[int, int, int]
ColorA = tuple[int, int, int, int]

# Outlined text is the same handful of static strings drawn every frame, and an
# outline of thickness t costs (2t+1)^2 glyph blits each time. Composing each
# label onto its own little surface once and reusing it turns a frame's worth of
# text into a few plain blits -- the menus were spending most of their frame
# budget here, which kept the loop from ever sleeping and starved the audio
# thread. The key includes everything that changes the pixels; fonts live in the
# asset cache for the whole run, so id(font) is stable.
_text_cache: dict[tuple, tuple[pygame.Surface, int, int]] = {}


def DrawTextWithOutline(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    position: tuple[int, int],
    fill: Color,
    outline: Color,
    thickness: int = 2,
) -> pygame.Rect:
    key = (id(font), text, fill, outline, thickness)
    cached = _text_cache.get(key)

    if cached is None:
        base = font.render(text, True, fill)
        edge = font.render(text, True, outline)
        base_w, base_h = base.get_size()
        composed = pygame.Surface((base_w + thickness * 2, base_h + thickness * 2), pygame.SRCALPHA)

        for offset_x in range(-thickness, thickness + 1):
            for offset_y in range(-thickness, thickness + 1):
                if offset_x != 0 or offset_y != 0:
                    composed.blit(edge, (thickness + offset_x, thickness + offset_y))

        composed.blit(base, (thickness, thickness))
        cached = (composed, base_w, base_h)
        _text_cache[key] = cached

    composed, base_w, base_h = cached
    x, y = position
    surface.blit(composed, (x - thickness, y - thickness))
    return pygame.Rect(x, y, base_w, base_h)


def MeasureText(font: pygame.font.Font, text: str) -> tuple[int, int]:
    return font.size(text)


def DrawSlantedPanel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    fill: ColorA,
    border: Color,
    slant: int = 14,
    border_width: int = 3,
) -> None:
    """Draws the angular parallelogram panel that defines the menu look."""
    points = [
        (rect.left + slant, rect.top),
        (rect.right, rect.top),
        (rect.right - slant, rect.bottom),
        (rect.left, rect.bottom),
    ]
    panel = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    pygame.draw.polygon(panel, fill, points)
    surface.blit(panel, (0, 0))

    if border_width > 0:
        pygame.draw.polygon(surface, border, points, border_width)


def DrawBar(
    surface: pygame.Surface,
    rect: pygame.Rect,
    ratio: float,
    fill: Color,
    background: Color,
    border: Color,
) -> None:
    clamped = min(max(ratio, 0.0), 1.0)
    pygame.draw.rect(surface, background, rect)
    inner = pygame.Rect(rect.left, rect.top, int(rect.width * clamped), rect.height)
    pygame.draw.rect(surface, fill, inner)
    pygame.draw.rect(surface, border, rect, 2)


# A gradient is fixed once its size and endpoints are known, but it was being
# rebuilt line by line every frame. Render each distinct gradient once and blit
# the cached copy thereafter.
_gradient_cache: dict[tuple, pygame.Surface] = {}


def FillVerticalGradient(surface: pygame.Surface, top: Color, bottom: Color) -> None:
    width = surface.get_width()
    height = surface.get_height()
    key = (width, height, top, bottom)
    gradient = _gradient_cache.get(key)

    if gradient is None:
        gradient = pygame.Surface((width, height))
        for y in range(height):
            blend = y / max(height - 1, 1)
            red = int(top[0] + (bottom[0] - top[0]) * blend)
            green = int(top[1] + (bottom[1] - top[1]) * blend)
            blue = int(top[2] + (bottom[2] - top[2]) * blend)
            pygame.draw.line(gradient, (red, green, blue), (0, y), (width, y))
        _gradient_cache[key] = gradient

    surface.blit(gradient, (0, 0))
