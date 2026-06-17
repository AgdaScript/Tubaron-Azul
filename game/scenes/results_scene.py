from __future__ import annotations
import pygame
from engine.rendering.draw import DrawTextWithOutline, DrawSlantedPanel
from game.scenes.base import GameScene
from game.scenes.services import GameContext
from game.scenes.decor import DrawMenuBackground
from game.persistence.records import RecordEntry
from game.data import theme
from game.match.match import Match


class ResultsScene(GameScene):
    """The final whistle for a single match.

    For a friendly it just shows the score. In a World Cup run it applies the
    result to the run and routes to the next stage or the end-of-run screen.
    """

    def __init__(self, ctx: GameContext, match: Match, stage_index: int) -> None:
        super().__init__(ctx)
        self._elapsed = 0.0
        self._home = match.score[0]
        self._away = match.score[1]
        self._won = match.HomeWon()
        self._draw = match.IsDraw()
        self._home_name = match.home.name
        self._away_name = match.away.name
        self._stage_index = stage_index
        self._is_tournament = stage_index >= 0
        self._applied = False

    def OnEnter(self) -> None:
        self.app.GetAudio().PlayMusic(theme.MUSIC_ANTHEM, theme.MUSIC_ANTHEM_VOLUME)

        if self._is_tournament and not self._applied:
            self._applied = True
            self.ctx.GetState().RecordMatch(self._home, self._away, self._won)
            self._SaveIfContinuing()

    def _SaveIfContinuing(self) -> None:
        state = self.ctx.GetState()
        if not state.finished:
            try:
                self.ctx.save_manager.Save(state)
            except Exception:
                pass

    def Update(self, dt: float) -> None:
        self._elapsed += dt

    def HandleEvent(self, event: pygame.event.Event) -> None:
        if self.HandleMuteInput(event):
            return

        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
            self._Advance()

    def _Advance(self) -> None:
        if not self._is_tournament:
            from game.scenes.title_scene import TitleScene
            self.app.GetScenes().RequestReplace(TitleScene(self.ctx))
            return

        state = self.ctx.GetState()
        if state.finished:
            self.app.GetScenes().RequestReplace(TournamentEndScene(self.ctx))
        else:
            from game.scenes.tournament_scene import TournamentScene
            self.app.GetScenes().RequestReplace(TournamentScene(self.ctx))

    def _Headline(self) -> tuple[str, tuple[int, int, int]]:
        if self._draw:
            return ("EMPATE", theme.OFF_WHITE)
        if self._won:
            return ("VITÓRIA!", theme.CV_YELLOW)
        return ("DERROTA", theme.RED)

    def Render(self, surface: pygame.Surface) -> None:
        DrawMenuBackground(surface, self._elapsed)
        headline, color = self._Headline()
        font = self.ctx.fonts.GetDisplay(78)
        width = font.size(headline)[0]
        DrawTextWithOutline(surface, font, headline, (theme.SCREEN_WIDTH // 2 - width // 2, 84), color, theme.INK, 4)

        score = f"{self._home}  -  {self._away}"
        sfont = self.ctx.fonts.GetDisplay(96)
        sw = sfont.size(score)[0]
        DrawTextWithOutline(surface, sfont, score, (theme.SCREEN_WIDTH // 2 - sw // 2, 196), theme.CV_WHITE, theme.INK, 4)

        names = f"{self._home_name}   x   {self._away_name}"
        nfont = self.ctx.fonts.GetBold(28)
        nw = nfont.size(names)[0]
        DrawTextWithOutline(surface, nfont, names, (theme.SCREEN_WIDTH // 2 - nw // 2, 320), theme.OFF_WHITE, theme.INK, 2)

        if self._is_tournament and not self._won:
            DrawTextWithOutline(surface, self.ctx.fonts.GetBold(24), "Era preciso vencer para avançar...",
                                (theme.SCREEN_WIDTH // 2 - 180, 372), theme.OFF_WHITE, theme.INK, 1)

        prompt = "ENTER para continuar"
        pfont = self.ctx.fonts.GetBold(24)
        pw = pfont.size(prompt)[0]
        DrawTextWithOutline(surface, pfont, prompt, (theme.SCREEN_WIDTH // 2 - pw // 2, 472), theme.CV_YELLOW, theme.INK, 2)
        self.DrawMuteControl(surface)


class TournamentEndScene(GameScene):
    """End of a World Cup run: champion or knocked out, plus a high-score entry."""

    def __init__(self, ctx: GameContext) -> None:
        super().__init__(ctx)
        self._elapsed = 0.0
        self._name = "CPV"
        self._saved = False
        self._rank = 0
        state = ctx.GetState()
        self._champion = state.champion
        self._score = state.Score()
        self._stage = state.StageReached()
        self._qualifies = ctx.records.QualifiesForRecord(self._score)

    def OnEnter(self) -> None:
        self.app.GetAudio().PlayMusic(theme.MUSIC_ANTHEM, theme.MUSIC_ANTHEM_VOLUME)
        self.ctx.save_manager.Delete()

    def Update(self, dt: float) -> None:
        self._elapsed += dt

    def HandleEvent(self, event: pygame.event.Event) -> None:
        editing_name = not self._saved and self._qualifies
        if self.HandleMuteInput(event, allow_key=not editing_name):
            return

        if event.type != pygame.KEYDOWN:
            return

        if editing_name:
            self._EditName(event)

        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._Confirm()

    def _EditName(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_BACKSPACE:
            self._name = self._name[:-1]
        elif event.unicode.isalnum() and len(self._name) < 8:
            self._name = self._name + event.unicode.upper()

    def _Confirm(self) -> None:
        if self._qualifies and not self._saved:
            name = self._name
            if not name:
                name = "CPV"
            outcome = "campeão"
            if not self._champion:
                outcome = "eliminado"
            self._rank = self.ctx.records.AddRecord(RecordEntry(name, self._score, self._stage, outcome))
            self._saved = True
            return

        from game.scenes.title_scene import TitleScene
        self.app.GetScenes().RequestReplace(TitleScene(self.ctx))

    def Render(self, surface: pygame.Surface) -> None:
        DrawMenuBackground(surface, self._elapsed)

        if self._champion:
            title = "CAMPEÕES DO MUNDO!"
            color = theme.CV_YELLOW
        else:
            title = "FIM DA CAMINHADA"
            color = theme.CV_WHITE

        font = self.ctx.fonts.GetDisplay(64)
        tw = font.size(title)[0]
        DrawTextWithOutline(surface, font, title, (theme.SCREEN_WIDTH // 2 - tw // 2, 70), color, theme.INK, 4)

        info = f"Pontuação: {self._score}"
        ifont = self.ctx.fonts.GetDisplay(40)
        iw = ifont.size(info)[0]
        DrawTextWithOutline(surface, ifont, info, (theme.SCREEN_WIDTH // 2 - iw // 2, 190), theme.CV_WHITE, theme.INK, 3)

        if self._qualifies and not self._saved:
            self._DrawNameEntry(surface)
        elif self._saved:
            msg = f"Recorde guardado — #{self._rank}"
            mw = self.ctx.fonts.GetBold(28).size(msg)[0]
            DrawTextWithOutline(surface, self.ctx.fonts.GetBold(28), msg, (theme.SCREEN_WIDTH // 2 - mw // 2, 280), theme.GREEN, theme.INK, 2)

        prompt = "ENTER"
        pfont = self.ctx.fonts.GetBold(24)
        pw = pfont.size(prompt)[0]
        DrawTextWithOutline(surface, pfont, prompt, (theme.SCREEN_WIDTH // 2 - pw // 2, 474), theme.CV_YELLOW, theme.INK, 2)
        self.DrawMuteControl(surface)

    def _DrawNameEntry(self, surface: pygame.Surface) -> None:
        label = "Novo recorde! Escreve o teu nome:"
        lw = self.ctx.fonts.GetBold(26).size(label)[0]
        DrawTextWithOutline(surface, self.ctx.fonts.GetBold(26), label, (theme.SCREEN_WIDTH // 2 - lw // 2, 274), theme.OFF_WHITE, theme.INK, 2)

        box = pygame.Rect(theme.SCREEN_WIDTH // 2 - 120, 318, 240, 56)
        DrawSlantedPanel(surface, box, (*theme.CV_WHITE, 240), theme.CV_BLUE, 14, 0)
        caret = self._name
        if int(self._elapsed * 2) % 2 == 0:
            caret = caret + "_"
        cw = self.ctx.fonts.GetDisplay(40).size(caret)[0]
        DrawTextWithOutline(surface, self.ctx.fonts.GetDisplay(40), caret, (box.centerx - cw // 2, box.top + 6), theme.CV_BLUE, theme.CV_BLUE, 0)
