from __future__ import annotations
import math
import random
import pygame
from engine.rendering.draw import DrawTextWithOutline, FillVerticalGradient
from game.scenes.base import GameScene
from game.scenes.services import GameContext
from game.data import theme

"""The opening montage — a short, skippable hype reel over IShowSpeed's anthem.

Redone for the live-football game: TV static resolving into the Tubarões logo,
the captain and the unbeatable Vozinha, a pitch rush, and the title card. It is
built as a timeline of segments, each drawn from its own local progress, with
scanlines and a vignette over everything for that broadcast feel. Esc / Space /
Enter / click skips straight to the title.
"""


class CinematicScene(GameScene):
    def __init__(self, ctx: GameContext) -> None:
        super().__init__(ctx)
        self._elapsed = 0.0
        self._flash = 0.0
        self._segment_index = 0
        self._idle = self.app.GetAssets().LoadImage("players/outfield_idle.png")
        self._keeper = self.app.GetAssets().LoadImage("players/keeper.png")
        self._crest = self.app.GetAssets().LoadImage("capeverde/crest.png")
        self._flag = self.app.GetAssets().LoadImage("capeverde/flag.png")
        self._idle = pygame.transform.smoothscale(self._idle, (250, 345))
        self._keeper = pygame.transform.smoothscale(self._keeper, (430, 254))
        self._scanlines = self._BuildScanlines()
        self._vignette = self._BuildVignette()
        self._segments = [
            (3.0, self._DrawStatic),
            (3.6, self._DrawLogo),
            (4.2, self._DrawCaptain),
            (4.2, self._DrawVozinha),
            (3.6, self._DrawPitchRush),
            (5.4, self._DrawTitleCard),
        ]
        self._total = sum(duration for duration, _ in self._segments)

    def OnEnter(self) -> None:
        self.app.GetAudio().PlayMusic(theme.MUSIC_OPENING, theme.MUSIC_OPENING_VOLUME)

    def HandleEvent(self, event: pygame.event.Event) -> None:
        if self.HandleMuteInput(event):
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            self._Finish()
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN, pygame.K_z):
            self._Finish()

    def Update(self, dt: float) -> None:
        self._elapsed += dt
        self._flash = max(0.0, self._flash - dt)

        index, _ = self._Locate()
        if index != self._segment_index:
            self._segment_index = index
            self._flash = 0.35

        if self._elapsed >= self._total:
            self._Finish()

    def _Finish(self) -> None:
        from game.scenes.title_scene import TitleScene
        self.app.GetScenes().RequestReplace(TitleScene(self.ctx))

    def _Locate(self) -> tuple[int, float]:
        clock = self._elapsed
        for index, (duration, _) in enumerate(self._segments):
            if clock < duration:
                return (index, clock / duration)
            clock -= duration

        return (len(self._segments) - 1, 1.0)

    # -- rendering -------------------------------------------------------

    def Render(self, surface: pygame.Surface) -> None:
        FillVerticalGradient(surface, theme.CV_BLUE, theme.CV_BLUE_DEEP)
        index, progress = self._Locate()
        self._segments[index][1](surface, progress)
        surface.blit(self._scanlines, (0, 0))
        surface.blit(self._vignette, (0, 0))

        if self._flash > 0.0:
            veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            veil.fill((255, 255, 255, int(220 * (self._flash / 0.35))))
            surface.blit(veil, (0, 0))

        DrawTextWithOutline(surface, self.ctx.fonts.GetBody(18), "ESPAÇO para saltar", (theme.SCREEN_WIDTH - 220, theme.SCREEN_HEIGHT - 30), theme.OFF_WHITE, theme.INK, 1)
        self.DrawMuteControl(surface)

    def _DrawStatic(self, surface: pygame.Surface, t: float) -> None:
        density = int(2600 * (1.0 - t))
        for _ in range(density):
            x = random.randint(0, theme.SCREEN_WIDTH - 1)
            y = random.randint(0, theme.SCREEN_HEIGHT - 1)
            shade = random.randint(120, 255)
            surface.set_at((x, y), (shade, shade, shade))

        alpha = int(255 * min(1.0, t * 1.6))
        font = self.ctx.fonts.GetDisplay(150)
        text = font.render("2026", True, theme.CV_WHITE)
        text.set_alpha(alpha)
        surface.blit(text, (theme.SCREEN_WIDTH // 2 - text.get_width() // 2, 180))

    def _DrawLogo(self, surface: pygame.Surface, t: float) -> None:
        ease = self._Ease(t)
        left_x = int(-400 + ease * 460)
        right_x = int(theme.SCREEN_WIDTH - ease * 540)
        DrawTextWithOutline(surface, self.ctx.fonts.GetDisplay(96), "OS TUBARÕES", (left_x, 150), theme.CV_WHITE, theme.CV_BLUE_DEEP, 4)
        DrawTextWithOutline(surface, self.ctx.fonts.GetDisplay(96), "AZUIS", (right_x, 250), theme.CV_YELLOW, theme.INK, 4)

    def _DrawCaptain(self, surface: pygame.Surface, t: float) -> None:
        self._DrawSpeedLines(surface, t)
        ease = self._Ease(min(1.0, t * 1.4))
        x = int(theme.SCREEN_WIDTH - ease * 360)
        surface.blit(self._idle, (x, 150))
        if t > 0.3:
            DrawTextWithOutline(surface, self.ctx.fonts.GetDisplay(64), "RYAN MENDES", (70, 200), theme.CV_WHITE, theme.CV_BLUE_DEEP, 3)
            DrawTextWithOutline(surface, self.ctx.fonts.GetBold(34), "CAPITÃO · Nº 10", (74, 270), theme.CV_YELLOW, theme.INK, 2)

    def _DrawVozinha(self, surface: pygame.Surface, t: float) -> None:
        self._DrawSpeedLines(surface, t)
        scale = 0.7 + 0.3 * self._Ease(min(1.0, t * 1.5))
        keeper = pygame.transform.rotozoom(self._keeper, 0, scale)
        surface.blit(keeper, (theme.SCREEN_WIDTH // 2 - keeper.get_width() // 2, 150))
        DrawTextWithOutline(surface, self.ctx.fonts.GetDisplay(80), "VOZINHA", (theme.SCREEN_WIDTH // 2 - 170, 70), theme.CV_YELLOW, theme.INK, 4)
        if t > 0.45:
            stamp = self.ctx.fonts.GetDisplay(58).render("INVENCÍVEL", True, theme.CV_WHITE)
            stamp = pygame.transform.rotate(stamp, 9)
            surface.blit(stamp, (560, 360))

    def _DrawPitchRush(self, surface: pygame.Surface, t: float) -> None:
        offset = int(t * 1200) % 160
        for index in range(-1, 8):
            x = index * 160 - offset
            color = theme.CV_BLUE_BRIGHT
            if index % 2 == 0:
                color = theme.CV_BLUE
            pygame.draw.polygon(surface, color, [(x, 0), (x + 160, 0), (x + 80, theme.SCREEN_HEIGHT), (x - 80, theme.SCREEN_HEIGHT)])

        self._DrawSpeedLines(surface, t)
        pop = self._Ease(min(1.0, t * 2.0))
        size = int(40 + pop * 90)
        DrawTextWithOutline(surface, self.ctx.fonts.GetDisplay(size), "GOLO!", (theme.SCREEN_WIDTH // 2 - size, 200), theme.CV_YELLOW, theme.INK, 4)

    def _DrawTitleCard(self, surface: pygame.Surface, t: float) -> None:
        crest = pygame.transform.smoothscale(self._crest, (150, 170))
        surface.blit(crest, (theme.SCREEN_WIDTH // 2 - 75, 30))
        DrawTextWithOutline(surface, self.ctx.fonts.GetDisplay(92), "CABO VERDE", (theme.SCREEN_WIDTH // 2 - 270, 210), theme.CV_WHITE, theme.CV_BLUE_DEEP, 4)
        DrawTextWithOutline(surface, self.ctx.fonts.GetDisplay(60), "MUNDIAL 2026", (theme.SCREEN_WIDTH // 2 - 180, 300), theme.CV_YELLOW, theme.INK, 3)
        flag = pygame.transform.scale(self._flag, (120, 72))
        surface.blit(flag, (theme.SCREEN_WIDTH // 2 - 60, 372))

        if int(self._elapsed * 2) % 2 == 0:
            prompt = "PRIME ESPAÇO PARA COMEÇAR"
            width = self.ctx.fonts.GetBold(26).size(prompt)[0]
            DrawTextWithOutline(surface, self.ctx.fonts.GetBold(26), prompt, (theme.SCREEN_WIDTH // 2 - width // 2, 470), theme.CV_WHITE, theme.INK, 2)

    def _DrawSpeedLines(self, surface: pygame.Surface, t: float) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for index in range(14):
            y = (index * 47 + int(t * 600)) % theme.SCREEN_HEIGHT
            pygame.draw.line(overlay, (255, 255, 255, 26), (0, y), (theme.SCREEN_WIDTH, y - 30), 3)
        surface.blit(overlay, (0, 0))

    def _Ease(self, t: float) -> float:
        clamped = min(1.0, max(0.0, t))
        return 1.0 - (1.0 - clamped) ** 3

    def _BuildScanlines(self) -> pygame.Surface:
        lines = pygame.Surface((theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT), pygame.SRCALPHA)
        for y in range(0, theme.SCREEN_HEIGHT, 3):
            pygame.draw.line(lines, (0, 0, 20, 46), (0, y), (theme.SCREEN_WIDTH, y))
        return lines

    def _BuildVignette(self) -> pygame.Surface:
        vignette = pygame.Surface((theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT), pygame.SRCALPHA)
        for radius in range(0, 260, 6):
            alpha = int(2 + radius * 0.32)
            pygame.draw.rect(vignette, (0, 6, 24, min(120, alpha)), pygame.Rect(radius, radius, theme.SCREEN_WIDTH - radius * 2, theme.SCREEN_HEIGHT - radius * 2), 6)
        return vignette
