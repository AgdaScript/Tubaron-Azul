from __future__ import annotations
import pygame
from engine.rendering.draw import DrawTextWithOutline
from game.scenes.base import GameScene
from game.scenes.services import GameContext
from game.scenes.menu import Menu, MenuOption
from game.data import theme


class PauseScene(GameScene):
    """Overlay paused over a running match: resume or abandon to the menu."""

    def __init__(self, ctx: GameContext) -> None:
        super().__init__(ctx)
        self._menu = Menu([
            MenuOption("CONTINUAR", "resume"),
            MenuOption("SAIR PARA O MENU", "quit"),
        ])

    def IsOpaque(self) -> bool:
        return False

    def HandleEvent(self, event: pygame.event.Event) -> None:
        if self.HandleMuteInput(event):
            return

        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_UP, pygame.K_w):
            self._menu.MoveUp()
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._menu.MoveDown()
        elif event.key == pygame.K_ESCAPE:
            self.app.GetScenes().RequestPop()
        elif event.key in (pygame.K_RETURN, pygame.K_z, pygame.K_SPACE):
            self._Confirm()

    def _Confirm(self) -> None:
        if self._menu.GetSelectedValue() == "resume":
            self.app.GetScenes().RequestPop()
            return

        from game.scenes.title_scene import TitleScene
        self.app.GetScenes().RequestClearTo(TitleScene(self.ctx))

    def Render(self, surface: pygame.Surface) -> None:
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((*theme.CV_BLUE_DEEP, 200))
        surface.blit(veil, (0, 0))

        title = "PAUSA"
        font = self.ctx.fonts.GetDisplay(72)
        tw = font.size(title)[0]
        DrawTextWithOutline(surface, font, title, (theme.SCREEN_WIDTH // 2 - tw // 2, 120), theme.CV_WHITE, theme.INK, 4)
        self._menu.Draw(surface, self.ctx.fonts, self.ctx.cursor, (theme.SCREEN_WIDTH // 2 - 150, 250), 300)
        self.DrawMuteControl(surface)
