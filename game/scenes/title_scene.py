from __future__ import annotations
import random
import pygame
from engine.rendering.draw import DrawTextWithOutline
from game.scenes.base import GameScene
from game.scenes.services import GameContext
from game.scenes.menu import Menu, MenuOption
from game.scenes.decor import DrawMenuBackground
from game.domain.game_state import GameState
from game.data import theme
from game.data.teams import GetCapeVerde, GetRival, WORLD_CUP_PATH


class TitleScene(GameScene):
    """Entry screen: start a World Cup run, continue, play a friendly, records."""

    def __init__(self, ctx: GameContext) -> None:
        super().__init__(ctx)
        self._elapsed = 0.0
        self._crest = self.app.GetAssets().LoadImage("capeverde/crest.png")
        self._flag = self.app.GetAssets().LoadImage("capeverde/flag.png")
        self._player = self.app.GetAssets().LoadImage("players/outfield_idle.png")
        self._player = pygame.transform.smoothscale(self._player, (210, 290))
        self._menu = self._BuildMenu()

    def _BuildMenu(self) -> Menu:
        has_save = self.ctx.save_manager.HasSave()
        return Menu([
            MenuOption("NOVO MUNDIAL", "new"),
            MenuOption("CONTINUAR", "continue", has_save),
            MenuOption("JOGO RÁPIDO", "quick"),
            MenuOption("RECORDES", "records"),
            MenuOption("SAIR", "quit"),
        ])

    def OnEnter(self) -> None:
        self.app.GetAudio().PlayMusic(theme.MUSIC_ANTHEM, theme.MUSIC_ANTHEM_VOLUME)

    def OnResume(self) -> None:
        self._menu = self._BuildMenu()
        self.app.GetAudio().PlayMusic(theme.MUSIC_ANTHEM, theme.MUSIC_ANTHEM_VOLUME)

    def Update(self, dt: float) -> None:
        self._elapsed += dt

    def HandleEvent(self, event: pygame.event.Event) -> None:
        if self.HandleMuteInput(event):
            return

        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_UP, pygame.K_w):
            self._menu.MoveUp()
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._menu.MoveDown()
        elif event.key in (pygame.K_RETURN, pygame.K_z, pygame.K_SPACE):
            self._Confirm()

    def _Confirm(self) -> None:
        choice = self._menu.GetSelectedValue()

        if choice == "new":
            self._StartTournament()
        elif choice == "continue":
            self._ContinueTournament()
        elif choice == "quick":
            self._StartQuickMatch()
        elif choice == "records":
            self._OpenRecords()
        elif choice == "quit":
            self.app.RequestQuit()

    def _StartTournament(self) -> None:
        from game.scenes.tournament_scene import TournamentScene
        self.ctx.state = GameState()
        self.app.GetScenes().RequestReplace(TournamentScene(self.ctx))

    def _ContinueTournament(self) -> None:
        from game.scenes.tournament_scene import TournamentScene
        try:
            self.ctx.state = self.ctx.save_manager.Load()
        except Exception:
            self.ctx.state = GameState()
        self.app.GetScenes().RequestReplace(TournamentScene(self.ctx))

    def _StartQuickMatch(self) -> None:
        from game.scenes.match_scene import MatchScene
        rival_id = random.choice(WORLD_CUP_PATH)
        self.app.GetScenes().RequestReplace(MatchScene(self.ctx, GetCapeVerde(), GetRival(rival_id), -1))

    def _OpenRecords(self) -> None:
        from game.scenes.records_scene import RecordsScene
        self.app.GetScenes().RequestPush(RecordsScene(self.ctx))

    def Render(self, surface: pygame.Surface) -> None:
        DrawMenuBackground(surface, self._elapsed)
        surface.blit(self._player, (688, 196))
        surface.blit(self._crest, (724, 96))
        surface.blit(pygame.transform.scale(self._flag, (120, 72)), (60, 470))

        DrawTextWithOutline(surface, self.ctx.fonts.GetDisplay(86), "CABO VERDE", (60, 56), theme.CV_WHITE, theme.CV_BLUE_DEEP, 3)
        DrawTextWithOutline(surface, self.ctx.fonts.GetDisplay(58), "MUNDIAL 2026", (62, 138), theme.CV_YELLOW, theme.INK, 3)
        DrawTextWithOutline(surface, self.ctx.fonts.GetBold(22), "Os Tubarões Azuis — futebol ao vivo", (66, 206), theme.CV_WHITE, theme.INK, 2)
        self._menu.Draw(surface, self.ctx.fonts, self.ctx.cursor, (96, 250), 300)
        DrawTextWithOutline(surface, self.ctx.fonts.GetBody(18), "Setas / WASD  -  Enter para confirmar", (200, 506), theme.OFF_WHITE, theme.INK, 1)
        self.DrawMuteControl(surface)
