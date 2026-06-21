from __future__ import annotations
import math
import pygame
from engine.mathx.vec2 import Vec2
from engine.rendering.camera import Camera
from engine.rendering.draw import DrawTextWithOutline
from game.scenes.base import GameScene
from game.scenes.services import GameContext
from game.data import theme
from game.data.teams import TeamDef
from game.match import pitch
from game.match.match import Match, MatchInput, STATE_KICKOFF, STATE_GOAL, STATE_PLAYING
from game.match.entities import Player, Ball
from game.visual import pitch_render
from game.visual.soccer_art import SpriteFactory, TeamSprites

"""The live match: reads the keyboard, drives the simulation, draws everything.

Movement is the arrow keys or WASD; the active man is always the one nearest the
ball. Left hand acts (pass / shoot / tackle), right hand steers.
"""

_MOVE_LEFT = (pygame.K_LEFT, pygame.K_a)
_MOVE_RIGHT = (pygame.K_RIGHT, pygame.K_d)
_MOVE_UP = (pygame.K_UP, pygame.K_w)
_MOVE_DOWN = (pygame.K_DOWN, pygame.K_s)
_SHOOT = (pygame.K_SPACE, pygame.K_k)
_PASS = (pygame.K_z, pygame.K_j)
_SWITCH = (pygame.K_x, pygame.K_l)


class MatchScene(GameScene):
    def __init__(self, ctx: GameContext, home: TeamDef, away: TeamDef, stage_index: int) -> None:
        super().__init__(ctx)
        self.match = Match(home, away)
        self.stage_index = stage_index
        self._camera = Camera(theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT)
        self._camera.SetBounds(pitch.WIDTH, pitch.HEIGHT)
        self._camera.CenterOn(self.match.ball.pos)
        self._factory = SpriteFactory(self.app.GetAssets())
        self._home_sprites = self._factory.GetTeamSprites(home.team_id, home.shirt, home.keeper)
        self._away_sprites = self._factory.GetTeamSprites(away.team_id, away.shirt, away.keeper)
        self._pitch = pitch_render.BuildPitchSurface()
        ball_img = self.app.GetAssets().LoadImage("pitch/ball.png")
        self._ball_img = pygame.transform.smoothscale(ball_img, (22, 22))
        self._flash = 0.0
        self._elapsed = 0.0
        self._result_handled = False

    def OnEnter(self) -> None:
        self.app.GetAudio().PlayMusic(theme.MUSIC_MATCH, theme.MUSIC_MATCH_VOLUME)

    def OnResume(self) -> None:
        self.app.GetAudio().PlayMusic(theme.MUSIC_MATCH, theme.MUSIC_MATCH_VOLUME)

    def HandleEvent(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            from game.scenes.pause_scene import PauseScene
            self.app.GetScenes().RequestPush(PauseScene(self.ctx))

    def Update(self, dt: float) -> None:
        self._elapsed += dt
        self._flash = max(0.0, self._flash - dt)
        previous_state = self.match.state
        self.match.Update(dt, self._ReadInput())

        if self.match.state == STATE_GOAL and previous_state != STATE_GOAL:
            self._flash = 0.4

        self._camera.FollowTarget(self.match.ball.pos, dt)

        if self.match.IsOver() and not self._result_handled:
            self._result_handled = True
            self._GoToResults()

    def _ReadInput(self) -> MatchInput:
        held = self.app.GetInput()
        dx = self._Axis(held, _MOVE_RIGHT) - self._Axis(held, _MOVE_LEFT)
        dy = self._Axis(held, _MOVE_DOWN) - self._Axis(held, _MOVE_UP)
        sprint = held.IsHeld(pygame.K_LSHIFT) or held.IsHeld(pygame.K_RSHIFT)
        return MatchInput(
            Vec2(dx, dy), sprint,
            self._Pressed(held, _SHOOT),
            self._Pressed(held, _PASS),
            self._Pressed(held, _SWITCH),
        )

    def _Axis(self, held, keys) -> float:
        for key in keys:
            if held.IsHeld(key):
                return 1.0

        return 0.0

    def _Pressed(self, held, keys) -> bool:
        for key in keys:
            if held.WasPressed(key):
                return True

        return False

    def _GoToResults(self) -> None:
        from game.scenes.results_scene import ResultsScene
        self.app.GetScenes().RequestReplace(ResultsScene(self.ctx, self.match, self.stage_index))

    # -- rendering -------------------------------------------------------

    def Render(self, surface: pygame.Surface) -> None:
        surface.fill((26, 70, 34))
        cam = self._camera.GetPosition()
        surface.blit(self._pitch, (int(-cam.x), int(-cam.y)))
        pitch_render.DrawGoals(surface, cam)
        self._DrawBallShadow(surface, cam)
        self._DrawPlayers(surface, cam)
        self._DrawBall(surface, cam)
        self._DrawHud(surface)
        self._DrawBanner(surface)

        if self._flash > 0.0:
            self._DrawFlash(surface)

    def _DrawPlayers(self, surface: pygame.Surface, cam: Vec2) -> None:
        ordered = sorted(self.match.players, key=lambda p: p.pos.y)

        for player in ordered:
            self._DrawShadow(surface, cam, player.pos)
            self._DrawPlayer(surface, cam, player)

    def _DrawPlayer(self, surface: pygame.Surface, cam: Vec2, player: Player) -> None:
        sprites = self._home_sprites
        if player.team_index == 1:
            sprites = self._away_sprites

        sprite = self._PickSprite(player, sprites)
        screen = self._camera.WorldToScreen(player.pos)

        if player.teleport_flash > 0.0:
            self._DrawTeleportFlash(surface, screen, player.teleport_flash)

        bob = 0
        if player.IsMoving() and not player.is_keeper:
            bob = int(abs(math.sin(player.run_phase)) * 4.0)

        x = int(screen.x - sprite.get_width() / 2)
        y = int(screen.y - sprite.get_height() + 6 - bob)
        surface.blit(sprite, (x, y))

        if player.controlled:
            self._DrawControlMarker(surface, screen, sprite.get_height())

    def _PickSprite(self, player: Player, sprites: TeamSprites) -> pygame.Surface:
        facing_right = player.facing >= 0.0

        if player.is_keeper:
            return self._PickKeeperSprite(player, sprites)

        if player.kick_timer > 0.0:
            if facing_right:
                return sprites.kick_right
            return sprites.kick_left

        if player.IsMoving():
            frames = sprites.run_right if facing_right else sprites.run_left
            index = int(player.run_phase) % len(frames)
            return frames[index]

        if facing_right:
            return sprites.idle_right
        return sprites.idle_left

    def _PickKeeperSprite(self, player: Player, sprites: TeamSprites) -> pygame.Surface:
        facing_right = player.facing >= 0.0

        if player.keeper_beaten_timer > 0.0:
            if facing_right:
                return sprites.keeper_beaten_right
            return sprites.keeper_beaten_left

        if player.kick_timer > 0.0:
            if facing_right:
                return sprites.keeper_dive_right
            return sprites.keeper_dive_left

        if pitch.BallInKeeperHalf(player.team_index, self.match.ball.pos.x):
            frames = sprites.keeper_run_right if facing_right else sprites.keeper_run_left
            index = int(player.run_phase) % len(frames)
            return frames[index]

        if facing_right:
            return sprites.keeper_idle_right
        return sprites.keeper_idle_left

    def _DrawControlMarker(self, surface: pygame.Surface, screen: Vec2, height: int) -> None:
        tip_y = int(screen.y - height - 4)
        cx = int(screen.x)
        points = [(cx, tip_y + 14), (cx - 9, tip_y), (cx + 9, tip_y)]
        pygame.draw.polygon(surface, theme.CV_YELLOW, points)
        pygame.draw.polygon(surface, theme.INK, points, 2)

    def _DrawTeleportFlash(self, surface: pygame.Surface, screen: Vec2, amount: float) -> None:
        radius = int(20 + (0.3 - amount) * 160)
        alpha = int(200 * (amount / 0.3))
        ring = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(ring, (*theme.CV_WHITE, alpha), (radius + 2, radius + 2), radius, 4)
        pygame.draw.circle(ring, (*theme.CV_YELLOW, alpha), (radius + 2, radius + 2), max(1, radius - 8), 2)
        surface.blit(ring, (int(screen.x - radius - 2), int(screen.y - 30 - radius)))

    def _DrawShadow(self, surface: pygame.Surface, cam: Vec2, world: Vec2) -> None:
        screen = self._camera.WorldToScreen(world)
        shadow = pygame.Surface((38, 16), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 90), shadow.get_rect())
        surface.blit(shadow, (int(screen.x - 19), int(screen.y - 8)))

    def _DrawBallShadow(self, surface: pygame.Surface, cam: Vec2) -> None:
        screen = self._camera.WorldToScreen(self.match.ball.pos)
        shadow = pygame.Surface((18, 9), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 110), shadow.get_rect())
        surface.blit(shadow, (int(screen.x - 9), int(screen.y - 4)))

    def _DrawBall(self, surface: pygame.Surface, cam: Vec2) -> None:
        ball = self.match.ball
        screen = self._camera.WorldToScreen(ball.pos)
        y = int(screen.y - self._ball_img.get_height() / 2 - ball.height)
        surface.blit(self._ball_img, (int(screen.x - self._ball_img.get_width() / 2), y))

    def _DrawHud(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(theme.SCREEN_WIDTH // 2 - 190, 14, 380, 54)
        board = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        board.fill((*theme.CV_BLUE_DEEP, 232))
        surface.blit(board, panel.topleft)
        pygame.draw.rect(surface, theme.CV_WHITE, panel, 2)

        score = f"{self.match.score[0]}  -  {self.match.score[1]}"
        DrawTextWithOutline(surface, self.ctx.fonts.GetDisplay(36), score,
                            (panel.centerx - self.ctx.fonts.GetDisplay(36).size(score)[0] // 2, panel.top + 6),
                            theme.CV_WHITE, theme.INK, 2)

        home = self.match.home.short
        away = self.match.away.short
        DrawTextWithOutline(surface, self.ctx.fonts.GetBold(26), home, (panel.left + 14, panel.top + 12), theme.CV_YELLOW, theme.INK, 2)
        away_w = self.ctx.fonts.GetBold(26).size(away)[0]
        DrawTextWithOutline(surface, self.ctx.fonts.GetBold(26), away, (panel.right - 14 - away_w, panel.top + 12), theme.CV_WHITE, theme.INK, 2)

        clock = f"{self.match.DisplayMinute()}'"
        clock_w = self.ctx.fonts.GetBold(24).size(clock)[0]
        DrawTextWithOutline(surface, self.ctx.fonts.GetBold(24), clock, (panel.centerx - clock_w // 2, panel.bottom - 4), theme.CV_WHITE, theme.INK, 2)

    def _DrawBanner(self, surface: pygame.Surface) -> None:
        state = self.match.state

        if state == STATE_GOAL:
            self._CenterBanner(surface, "GOLO!", theme.CV_YELLOW)
        elif state == STATE_KICKOFF:
            self._CenterBanner(surface, "PONTAPÉ DE SAÍDA", theme.CV_WHITE)

    def _CenterBanner(self, surface: pygame.Surface, text: str, color) -> None:
        font = self.ctx.fonts.GetDisplay(72)
        width = font.size(text)[0]
        x = theme.SCREEN_WIDTH // 2 - width // 2
        y = theme.SCREEN_HEIGHT // 2 - 70
        DrawTextWithOutline(surface, font, text, (x, y), color, theme.INK, 4)

    def _DrawFlash(self, surface: pygame.Surface) -> None:
        alpha = int(180 * (self._flash / 0.4))
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((255, 255, 255, alpha))
        surface.blit(veil, (0, 0))
