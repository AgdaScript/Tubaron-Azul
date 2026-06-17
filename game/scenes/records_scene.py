from __future__ import annotations
import pygame
from engine.rendering.draw import DrawTextWithOutline, DrawSlantedPanel
from game.scenes.base import GameScene
from game.scenes.services import GameContext
from game.scenes.decor import DrawMenuBackground, DrawHeaderBanner
from game.data import theme


class RecordsScene(GameScene):
    """Shows the saved high scores, highest first."""

    def __init__(self, ctx: GameContext) -> None:
        super().__init__(ctx)
        self._elapsed = 0.0
        self._entries = ctx.records.GetEntries()

    def Update(self, dt: float) -> None:
        self._elapsed += dt

    def HandleEvent(self, event: pygame.event.Event) -> None:
        if self.HandleMuteInput(event):
            return

        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_z, pygame.K_x):
            self.app.GetScenes().RequestPop()

    def Render(self, surface: pygame.Surface) -> None:
        DrawMenuBackground(surface, self._elapsed)
        DrawHeaderBanner(surface, self.ctx.fonts, "RECORDES", "Os melhores Mundiais")
        self._DrawEntries(surface)
        DrawTextWithOutline(surface, self.ctx.fonts.GetBody(18), "Enter para voltar", (44, 506), theme.OFF_WHITE, theme.INK, 1)
        self.DrawMuteControl(surface)

    def _DrawEntries(self, surface: pygame.Surface) -> None:
        font = self.ctx.fonts.GetBold(26)

        if not self._entries:
            DrawTextWithOutline(surface, font, "Ainda sem recordes. Sê o primeiro!", (60, 180), theme.CV_WHITE, theme.INK, 2)
            return

        for index, entry in enumerate(self._entries):
            rect = pygame.Rect(60, 130 + index * 44, 820, 38)
            DrawSlantedPanel(surface, rect, (*theme.CV_BLUE_DEEP, 205), theme.CV_WHITE, 12, 2)
            line = f"{index + 1:>2}.  {entry.name:<10}  {entry.score:>6} pts   {entry.StageLabel():<8}  {entry.outcome.upper()}"
            DrawTextWithOutline(surface, font, line, (rect.left + 16, rect.top + 4), theme.CV_WHITE, theme.INK, 1)
