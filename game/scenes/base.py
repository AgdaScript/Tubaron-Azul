from __future__ import annotations
import pygame
from engine.scene.scene import Scene
from game.scenes.services import GameContext
from game.scenes import mute_control


class GameScene(Scene):
    """Base for every game scene: carries the shared context to the next scene."""

    def __init__(self, ctx: GameContext) -> None:
        super().__init__(ctx.app)
        self.ctx = ctx

    def HandleMuteInput(self, event: pygame.event.Event, *, allow_key: bool = True) -> bool:
        return mute_control.HandleMuteInput(event, self.app.GetAudio(), allow_key=allow_key)

    def DrawMuteControl(self, surface: pygame.Surface) -> None:
        mute_control.DrawMuteControl(surface, self.app.GetAudio())
