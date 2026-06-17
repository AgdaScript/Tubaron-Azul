from __future__ import annotations
import pygame
from engine.rendering.draw import DrawTextWithOutline, DrawSlantedPanel
from game.scenes.base import GameScene
from game.scenes.services import GameContext
from game.scenes.decor import DrawMenuBackground, DrawHeaderBanner
from game.data import theme
from game.data.teams import GetCapeVerde, GetRival, WORLD_CUP_PATH


class TournamentScene(GameScene):
    """The World Cup road: the six stages, progress so far, the next opponent."""

    def __init__(self, ctx: GameContext) -> None:
        super().__init__(ctx)
        self._elapsed = 0.0

    def OnEnter(self) -> None:
        self.app.GetAudio().PlayMusic(theme.MUSIC_ANTHEM, theme.MUSIC_ANTHEM_VOLUME)
        self._CheckFinished()

    def OnResume(self) -> None:
        self.app.GetAudio().PlayMusic(theme.MUSIC_ANTHEM, theme.MUSIC_ANTHEM_VOLUME)
        self._CheckFinished()

    def _CheckFinished(self) -> None:
        state = self.ctx.GetState()

        if state.finished:
            from game.scenes.results_scene import TournamentEndScene
            self.app.GetScenes().RequestReplace(TournamentEndScene(self.ctx))

    def Update(self, dt: float) -> None:
        self._elapsed += dt

    def HandleEvent(self, event: pygame.event.Event) -> None:
        if self.HandleMuteInput(event):
            return

        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
            self._StartMatch()
        elif event.key == pygame.K_ESCAPE:
            self._SaveAndExit()

    def _StartMatch(self) -> None:
        from game.scenes.match_scene import MatchScene
        state = self.ctx.GetState()
        rival = GetRival(state.CurrentOpponentId())
        self.app.GetScenes().RequestReplace(MatchScene(self.ctx, GetCapeVerde(), rival, state.stage_index))

    def _SaveAndExit(self) -> None:
        from game.scenes.title_scene import TitleScene
        try:
            self.ctx.save_manager.Save(self.ctx.GetState())
        except Exception:
            pass
        self.app.GetScenes().RequestReplace(TitleScene(self.ctx))

    def Render(self, surface: pygame.Surface) -> None:
        DrawMenuBackground(surface, self._elapsed)
        DrawHeaderBanner(surface, self.ctx.fonts, "MUNDIAL 2026", "A estrada dos Tubarões Azuis")

        state = self.ctx.GetState()
        self._DrawRoad(surface, state)
        self._DrawNextMatch(surface, state)

        DrawTextWithOutline(surface, self.ctx.fonts.GetBody(18), "Enter: entrar em campo    Esc: guardar e sair", (40, 508), theme.OFF_WHITE, theme.INK, 1)
        self.DrawMuteControl(surface)

    def _DrawRoad(self, surface: pygame.Surface, state) -> None:
        top = 132
        for index, rival_id in enumerate(WORLD_CUP_PATH):
            rival = GetRival(rival_id)
            row = pygame.Rect(40, top + index * 52, 520, 44)
            played = index < state.stage_index
            current = index == state.stage_index

            if current:
                DrawSlantedPanel(surface, row, (*theme.CV_YELLOW, 235), theme.CV_BLUE, 14, 0)
                text_color = theme.CV_BLUE
            elif played:
                DrawSlantedPanel(surface, row, (*theme.CV_BLUE_DEEP, 215), theme.GREEN, 14, 2)
                text_color = theme.GREEN
            else:
                DrawSlantedPanel(surface, row, (*theme.CV_BLUE_DEEP, 170), theme.OFF_WHITE, 14, 2)
                text_color = theme.OFF_WHITE

            label = f"{index + 1}. {rival.name}  —  {rival.round_label}"
            DrawTextWithOutline(surface, self.ctx.fonts.GetBold(22), label, (row.left + 18, row.top + 8), text_color, theme.INK, 1)

            if played:
                DrawTextWithOutline(surface, self.ctx.fonts.GetBold(22), "VITÓRIA", (row.right - 90, row.top + 8), theme.GREEN, theme.INK, 1)

    def _DrawNextMatch(self, surface: pygame.Surface, state) -> None:
        rival = GetRival(state.CurrentOpponentId())
        box = pygame.Rect(596, 132, 324, 312)
        panel = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
        panel.fill((*theme.CV_BLUE_DEEP, 220))
        surface.blit(panel, box.topleft)
        pygame.draw.rect(surface, theme.CV_WHITE, box, 2)

        DrawTextWithOutline(surface, self.ctx.fonts.GetBold(22), "PRÓXIMO JOGO", (box.left + 20, box.top + 16), theme.CV_YELLOW, theme.INK, 2)
        DrawTextWithOutline(surface, self.ctx.fonts.GetDisplay(30), "CABO VERDE", (box.left + 20, box.top + 54), theme.CV_WHITE, theme.INK, 2)
        DrawTextWithOutline(surface, self.ctx.fonts.GetBold(26), "vs", (box.left + 20, box.top + 96), theme.OFF_WHITE, theme.INK, 1)

        swatch = pygame.Rect(box.left + 20, box.top + 134, 40, 40)
        pygame.draw.rect(surface, rival.shirt, swatch)
        pygame.draw.rect(surface, theme.CV_WHITE, swatch, 2)
        DrawTextWithOutline(surface, self.ctx.fonts.GetDisplay(30), rival.name.upper(), (box.left + 72, box.top + 130), theme.CV_WHITE, theme.INK, 2)

        DrawTextWithOutline(surface, self.ctx.fonts.GetBody(20), rival.round_label, (box.left + 20, box.top + 184), theme.OFF_WHITE, theme.INK, 1)
        DrawTextWithOutline(surface, self.ctx.fonts.GetBody(20), "Dificuldade", (box.left + 20, box.top + 214), theme.OFF_WHITE, theme.INK, 1)
        self._DrawDifficulty(surface, box.left + 138, box.top + 226, state.stage_index + 1)

        prompt = pygame.Rect(box.left + 20, box.bottom - 56, box.width - 40, 40)
        DrawSlantedPanel(surface, prompt, (*theme.CV_WHITE, 240), theme.CV_BLUE, 12, 0)
        DrawTextWithOutline(surface, self.ctx.fonts.GetBold(24), "ENTER — JOGAR", (prompt.left + 18, prompt.top + 6), theme.CV_BLUE, theme.INK, 1)

    def _DrawDifficulty(self, surface: pygame.Surface, x: int, y: int, level: int) -> None:
        for index in range(6):
            center = (x + index * 26, y)
            if index < level:
                pygame.draw.circle(surface, theme.CV_YELLOW, center, 8)
                pygame.draw.circle(surface, theme.INK, center, 8, 2)
            else:
                pygame.draw.circle(surface, theme.CV_BLUE_DEEP, center, 8)
                pygame.draw.circle(surface, theme.OFF_WHITE, center, 8, 2)
